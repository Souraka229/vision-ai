"""Pipeline temps réel : caméra -> mains -> gestes -> actions -> métriques -> JPEG."""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import deque

import cv2
import psutil

from backend.analytics.store import EventStore
from backend.app.settings import Settings
from backend.controllers.airmouse import AirMouse
from backend.controllers.computer import ComputerController
from backend.gestures.custom import CustomGestures
from backend.gestures.rules import classify
from backend.gestures.stabilizer import Stabilizer
from backend.vision.camera import Camera
from backend.vision.hands import HandTracker, draw_hand

log = logging.getLogger("engine")


class Engine:
    def __init__(self):
        self.settings = Settings()
        self.store = EventStore()
        self.control = ComputerController()
        self.air = AirMouse(self.control)
        self.custom = CustomGestures()
        self.camera: Camera | None = None
        self.hands: HandTracker | None = None
        self.objects = None  # détecteur YOLO, chargé à l'activation
        self.stab = Stabilizer()
        self.proc = psutil.Process(os.getpid())
        self._thread: threading.Thread | None = None
        self._run = False
        self._jpeg: bytes | None = None
        self._jpeg_lock = threading.Lock()
        self._lat = deque(maxlen=60)
        self.metrics: dict = {"fps": 0.0, "latency_ms": 0.0, "ram_mb": 0.0, "cpu": 0.0}
        self.state: dict = {"hands": [], "objects": [], "gesture": None, "confidence": 0.0}
        self.recording: dict | None = None  # {"name","target","count"}
        self.last_error: str | None = None
        self.proc.cpu_percent()

    # --- cycle de vie -------------------------------------------------
    def start(self) -> bool:
        if self._run:
            return True
        s = self.settings.data
        self.last_error = None
        if s.get("camera_source") == "phone":
            from backend.vision.phone import phone_source
            self.camera = phone_source
        else:
            self.camera = Camera(s["camera_index"], s["width"], s["height"], s["simulate"], s.get("camera_url", ""))
        if not self.camera.start():
            self.last_error = self.camera.error
            self.camera = None
            return False
        self._run = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="engine")
        self._thread.start()
        return True

    def stop(self) -> None:
        self._run = False
        if self._thread:
            self._thread.join(timeout=3)
        if self.camera:
            self.camera.stop()
            self.camera = None
        self._release_models()
        self.control.stop()
        with self._jpeg_lock:
            self._jpeg = None
        self.metrics.update(fps=0.0, latency_ms=0.0)

    def _release_models(self) -> None:
        if self.hands:
            self.hands.close()
            self.hands = None
        self.objects = None

    # --- boucle -------------------------------------------------------
    def _loop(self) -> None:
        seq, n, t0, frame_i = -1, 0, time.time(), 0
        last_gesture = None
        try:
            while self._run:
                seq, frame = self.camera.read(seq)
                if self.camera.error and not self.camera.running:
                    self.last_error = self.camera.error
                    break
                if frame is None:
                    time.sleep(0.004)
                    continue
                a = time.time()
                s = self.settings.data
                mods = s["modules"]
                self.stab.min_conf, self.stab.cooldown = s["min_confidence"], s["cooldown"]
                view = frame.copy()  # une seule copie pour dessiner
                hands_out = []
                if mods["hands"]:
                    if self.hands is None:
                        self.hands = HandTracker(s["max_hands"])
                    for h in self.hands.process(frame, int(time.time() * 1000))[: s["max_hands"]]:
                        g, c = classify(h.landmarks)
                        cg, cc = self.custom.predict(h.landmarks, h.handedness)
                        if cg and cc >= max(s["min_confidence"], c if g else 0):
                            g, c = cg, cc
                        hands_out.append({"handedness": h.handedness, "gesture": g, "confidence": round(c, 2),
                                          "x": float(h.landmarks[8][0]), "y": float(h.landmarks[8][1])})
                        draw_hand(view, h, f"{g or '?'} {c:.0%}")
                        self._on_hand(h, g, c, hands_out[-1])
                elif self.hands:
                    self.hands.close()
                    self.hands = None
                self._run_objects(frame, view, frame_i)
                frame_i += 1
                self.state["hands"] = hands_out
                self.state["gesture"] = self.stab.stable
                self.state["confidence"] = hands_out[0]["confidence"] if hands_out else 0.0
                if not hands_out:
                    self.air.release()
                    self.stab.update(None, 0)
                    if self.control.dragging:
                        self.control.drag(False)
                ok, buf = cv2.imencode(".jpg", view, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if ok:
                    with self._jpeg_lock:
                        self._jpeg = buf.tobytes()
                self._lat.append((time.time() - a) * 1000)
                n += 1
                if time.time() - t0 >= 1:
                    self._update_metrics(n / (time.time() - t0))
                    n, t0 = 0, time.time()
        except Exception as e:  # noqa: BLE001
            log.exception("boucle moteur")
            self.last_error = f"Erreur moteur: {e}"
        finally:
            self._run = False

    def _on_hand(self, h, g, c, info) -> None:
        stable, fire = self.stab.update(g, c)
        if self.recording:
            r = self.recording
            if r and r["count"] < r["target"] and time.time() - r.get("t", 0) > 0.15:
                r["count"] = self.custom.add_sample(r["name"], h.landmarks, h.handedness)
                r["t"] = time.time()
                if r["count"] >= r["target"]:
                    self.recording = None
            return  # pas de déclenchement d'actions pendant l'enregistrement
        s = self.settings.data
        if fire and stable:
            self.store.log("gesture", stable, c)
            action = s["gesture_actions"].get(stable) or s["custom_actions"].get(stable, "none")
            if action != "none":
                res = self.control.execute(action)
                if res == "executed":
                    self.store.log("command", action)
        if s["air_mouse"] and self.control.enabled and not info.get("secondary"):
            self.air.configure(s["air_smoothing"], s["air_margin"])
            res = self.air.update(h.landmarks, g)
            if "click" in res or "drag" in res:
                self.store.log("command", "air_click_" + str(res.get("click", "drag")))
        elif self.air.pinching or self.air.dragging:
            self.air.release()

    def _run_objects(self, frame, view, i: int) -> None:
        mods = self.settings.data["modules"]
        if not mods["objects"]:
            if self.objects:
                self.objects = None
                self.state["objects"] = []
            return
        if self.objects is None:
            try:
                from backend.vision.objects import ObjectDetector
                self.objects = ObjectDetector(model=self.settings.data.get("yolo_model", "yolov8n.onnx"))
            except Exception as e:  # noqa: BLE001
                self.last_error = f"YOLO indisponible: {e}"
                mods["objects"] = False
                return
        if i % self.settings.data["yolo_every_n"] == 0:
            dets = self.objects.detect(frame)
            self.state["objects"] = dets
            people = sum(d["label"] == "person" for d in dets)
            phones = sum(d["label"] == "cell phone" for d in dets)
            inter, new = self.objects.interactions(dets)
            self.store.log("people", "", people)
            self.store.log("phones", "", phones)
            for pid in new:  # une interaction n'est comptée qu'à son apparition
                self.store.log("interaction", f"personne #{pid} : téléphone visible")
            self.state["interactions"] = inter
        for d in self.state["objects"]:
            x1, y1, x2, y2 = d["box"]
            busy = d["label"] == "person" and any(i["person_id"] == d.get("id") for i in self.state.get("interactions", []))
            cv2.rectangle(view, (x1, y1), (x2, y2), (0, 0, 255) if busy else (30, 140, 255), 2)
            tag = f"#{d['id']} " if "id" in d else ""
            cv2.putText(view, f"{tag}{d['label']} {d['score']:.0%}" + (" TEL" if busy else ""), (x1, max(y1 - 6, 12)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    def _update_metrics(self, fps: float) -> None:
        lat = sum(self._lat) / len(self._lat) if self._lat else 0.0
        self.metrics = {"fps": round(fps, 1), "latency_ms": round(lat, 1),
                        "ram_mb": round(self.proc.memory_info().rss / 2**20, 1),
                        "cpu": round(self.proc.cpu_percent() / (os.cpu_count() or 1), 1)}
        self.store.log("fps", "", fps)
        self.store.log("latency", "", lat)
        self.store.log("ram", "", self.metrics["ram_mb"])

    def jpeg(self) -> bytes | None:
        with self._jpeg_lock:
            return self._jpeg

    @property
    def running(self) -> bool:
        return self._run

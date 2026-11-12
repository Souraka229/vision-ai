"""Détection YOLOv8n (ONNX Runtime, CPU) + suivi anonyme + interactions personne/téléphone.

Aucune reconnaissance faciale, aucune image conservée. Les IDs sont temporaires (mémoire seulement).
"""
from __future__ import annotations

import logging
from collections import deque
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger("vision.objects")
MODEL = Path(__file__).resolve().parents[1] / "models" / "yolov8n.onnx"
CLASSES = {0: "person", 24: "backpack", 56: "chair", 63: "laptop", 67: "cell phone"}


def _iou(a, b) -> float:
    x1, y1, x2, y2 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0.0


class ObjectDetector:
    def __init__(self, conf: float = 0.35, model: str = "yolov8n.onnx"):
        import onnxruntime as ort
        path = MODEL.parent / Path(model).name  # nom de fichier seulement : pas de chemin arbitraire
        if not path.exists():
            raise FileNotFoundError(f"Modèle {path.name} absent de backend/models/")
        so = ort.SessionOptions()
        so.intra_op_num_threads = 3  # laisse du CPU à MediaPipe
        self.sess = ort.InferenceSession(str(path), so, providers=["CPUExecutionProvider"])
        self.fp16 = "float16" in self.sess.get_inputs()[0].type
        self.conf = conf
        self._tracks: dict[int, tuple[list, int]] = {}  # id -> (box, frames_manquées)
        self._next_id = 1
        self._using: dict[int, int] = {}  # id -> passes sans téléphone
        self._hist: dict[int, deque] = {}

    def detect(self, bgr: np.ndarray) -> list[dict]:
        h, w = bgr.shape[:2]
        if bgr.mean() < 90:  # image sombre : égalisation locale du contraste (entrée du modèle seulement)
            lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
            lab[:, :, 0] = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(lab[:, :, 0])
            bgr = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        r = 640 / max(h, w)
        nh, nw = int(h * r), int(w * r)
        canvas = np.full((640, 640, 3), 114, np.uint8)
        canvas[:nh, :nw] = cv2.resize(bgr, (nw, nh))
        blob = cv2.dnn.blobFromImage(canvas, 1 / 255.0, swapRB=True)
        blob = blob.astype(np.float16 if self.fp16 else np.float32)
        out = self.sess.run(None, {"images": blob})[0][0].astype(np.float32).T  # (8400, 84)
        scores = out[:, 4:]
        ids = scores.argmax(1)
        conf = scores.max(1)
        thr = np.where(ids == 67, 0.30, 0.45)  # téléphone : petit, seuil plus bas ; autres : plus strict
        keep = np.isin(ids, list(CLASSES)) & (conf >= thr)
        out, ids, conf = out[keep], ids[keep], conf[keep]
        boxes = [[int((cx - bw / 2) / r), int((cy - bh / 2) / r), int(bw / r), int(bh / r)]
                 for cx, cy, bw, bh in out[:, :4]]
        idx = cv2.dnn.NMSBoxes(boxes, conf.tolist(), 0.30, 0.5) if boxes else []
        dets = []
        for i in np.array(idx).flatten():
            x, y, bw, bh = boxes[i]
            box = [max(x, 0), max(y, 0), min(x + bw, w), min(y + bh, h)]
            dets.append({"label": CLASSES[int(ids[i])], "score": float(conf[i]), "box": box})
        self._assign_ids([d for d in dets if d["label"] == "person"])
        return dets

    def _assign_ids(self, people: list[dict]) -> None:
        """Suivi glouton par IoU : ID anonyme et temporaire par personne."""
        used = set()
        for p in sorted(people, key=lambda d: -d["score"]):
            best, bi = 0.3, None
            for tid, (tb, _) in self._tracks.items():
                v = _iou(p["box"], tb)
                if tid not in used and v > best:
                    best, bi = v, tid
            if bi is None:
                bi, self._next_id = self._next_id, self._next_id + 1
            used.add(bi)
            self._tracks[bi] = (p["box"], 0)
            p["id"] = bi
        for tid in list(self._tracks):
            if tid not in used:
                b, miss = self._tracks[tid]
                if miss >= 15:
                    del self._tracks[tid]
                    self._using.pop(tid, None)
                else:
                    self._tracks[tid] = (b, miss + 1)

    def interactions(self, dets: list[dict]) -> tuple[list[dict], list[int]]:
        """Personne avec un téléphone visible dans sa zone haut/centre (main, visage ou torse).

        Estimation purement visuelle : ne dit rien de l'intention de la personne.
        Retourne (interactions courantes, IDs nouvellement observés).
        """
        phones = [d for d in dets if d["label"] == "cell phone" and d["score"] >= 0.40]
        seen = set()
        for p in (d for d in dets if d["label"] == "person"):
            x1, y1, x2, y2 = p["box"]
            h = y2 - y1
            for ph in phones:
                px1, py1, px2, py2 = ph["box"]
                area = max((px2 - px1) * (py2 - py1), 1)
                inter = max(0, min(x2, px2) - max(x1, px1)) * max(0, min(y2, py2) - max(y1, py1))
                cy = (py1 + py2) / 2
                small = area < 0.25 * (x2 - x1) * h  # un téléphone n'est pas grand par rapport au corps
                if inter / area >= 0.8 and y1 <= cy <= y1 + 0.85 * h and small:
                    seen.add(p["id"])
                    break
        # persistance : visible sur au moins 3 des 5 dernières passes (évite les faux positifs d'une image)
        for pid in {t for t in self._tracks}:
            hist = self._hist.setdefault(pid, deque(maxlen=5))
            hist.append(pid in seen)
        for pid in list(self._hist):
            if pid not in self._tracks:
                del self._hist[pid]
        current = [{"person_id": pid, "kind": "phone_visible_in_use", "label": f"Personne #{pid} : téléphone visible"}
                   for pid, hist in self._hist.items() if sum(hist) >= 3 and pid in seen]
        ids = {c["person_id"] for c in current}
        new = sorted(ids - set(self._using))
        for i in ids:
            self._using[i] = 0
        for i in list(self._using):  # tolérance : 4 passes sans téléphone avant de clore l'interaction
            if i not in ids:
                self._using[i] += 1
                if self._using[i] > 4:
                    del self._using[i]
        return current, new

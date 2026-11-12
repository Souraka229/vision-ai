"""Capture webcam threadée : ne garde que la dernière frame (buffer = 1)."""
from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import cv2
import numpy as np

log = logging.getLogger("vision.camera")


class Camera:
    def __init__(self, index: int = 0, width: int = 640, height: int = 480, simulate: bool = False, url: str = ""):
        self.index, self.width, self.height = index, width, height
        self.url = url.strip()
        self.simulate = simulate
        self.error: Optional[str] = None
        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None
        self._seq = 0
        self._run = False
        self._thread: Optional[threading.Thread] = None
        self.fps = 0.0

    @property
    def running(self) -> bool:
        return self._run

    def start(self) -> bool:
        if self._run:
            return True
        self.error = None
        if not self.simulate:
            if self.url:
                if not self.url.lower().startswith(("http://", "https://", "rtsp://")):
                    self.error = "L'URL doit commencer par http://, https:// ou rtsp://"
                    return False
                cap = cv2.VideoCapture(self.url)
            else:
                cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                self.error = f"Impossible d'ouvrir {'le flux ' + self.url if self.url else 'la caméra ' + str(self.index)}"
                log.error(self.error)
                return False
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self._cap = cap
        self._run = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="camera")
        self._thread.start()
        return True

    def _loop(self) -> None:
        last, n, t0 = time.time(), 0, time.time()
        fails = 0
        while self._run:
            if self.simulate:
                f = np.zeros((self.height, self.width, 3), np.uint8)
                cv2.putText(f, "SIMULATION - pas de camera", (60, self.height // 2),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (30, 140, 255), 2)
                time.sleep(1 / 15)
            else:
                ok, f = self._cap.read()
                if not ok:
                    fails += 1
                    if fails > 30:
                        self.error = "Flux caméra perdu"
                        self._run = False
                        break
                    time.sleep(0.03)
                    continue
                fails = 0
                if self.url and f.shape[1] != self.width:  # flux téléphone : ramené à la résolution configurée
                    f = cv2.resize(f, (self.width, int(f.shape[0] * self.width / f.shape[1])))
            with self._lock:
                self._frame, self._seq = f, self._seq + 1
            n += 1
            if time.time() - t0 >= 1:
                self.fps, n, t0 = n / (time.time() - t0), 0, time.time()

    def read(self, last_seq: int = -1):
        """Retourne (seq, frame) ; frame None si pas de nouvelle image."""
        with self._lock:
            if self._frame is None or self._seq == last_seq:
                return self._seq, None
            return self._seq, self._frame

    def stop(self) -> None:
        self._run = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._frame = None
        self.fps = 0.0

    @staticmethod
    def list_cameras(max_idx: int = 4) -> list[int]:
        found = []
        for i in range(max_idx):
            c = cv2.VideoCapture(i, cv2.CAP_DSHOW)
            if c.isOpened():
                found.append(i)
            c.release()
        return found

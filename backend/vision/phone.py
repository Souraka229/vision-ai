"""Source vidéo « téléphone » : reçoit des JPEG poussés par la page web du téléphone (même interface que Camera)."""
from __future__ import annotations

import threading
import time
from typing import Optional

import cv2
import numpy as np


class PhoneSource:
    simulate = False
    index = -1

    def __init__(self):
        self._lock = threading.Lock()
        self._frame: Optional[np.ndarray] = None
        self._seq = 0
        self.running = False
        self.error: Optional[str] = None
        self.last_frame_ts = 0.0
        self.fps = 0.0
        self._n, self._t0 = 0, time.time()

    @property
    def connected(self) -> bool:
        return time.time() - self.last_frame_ts < 3

    def push(self, jpeg: bytes) -> None:
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            return
        with self._lock:
            self._frame, self._seq = img, self._seq + 1
        self.last_frame_ts = time.time()
        self._n += 1
        if time.time() - self._t0 >= 1:
            self.fps, self._n, self._t0 = self._n / (time.time() - self._t0), 0, time.time()

    def start(self) -> bool:
        self.running, self.error = True, None
        return True

    def read(self, last_seq: int = -1):
        with self._lock:
            if self._frame is None or self._seq == last_seq:
                return self._seq, None
            return self._seq, self._frame

    def stop(self) -> None:
        self.running = False
        with self._lock:
            self._frame = None
        self.fps = 0.0


phone_source = PhoneSource()

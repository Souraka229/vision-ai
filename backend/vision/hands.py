"""MediaPipe Hand Landmarker (21 points), chargé à l'activation."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger("vision.hands")
MODEL = Path(__file__).resolve().parents[1] / "models" / "hand_landmarker.task"

CONNECTIONS = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8), (5, 9), (9, 10),
               (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16), (13, 17), (17, 18),
               (18, 19), (19, 20), (0, 17)]


@dataclass
class Hand:
    landmarks: np.ndarray  # (21,3) coordonnées normalisées image
    handedness: str        # "Left"/"Right" (vue miroir non appliquée)
    score: float


class HandTracker:
    def __init__(self, max_hands: int = 1, min_conf: float = 0.5):
        import mediapipe as mp
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision
        self._mp = mp
        opts = vision.HandLandmarkerOptions(
            base_options=mpp.BaseOptions(model_asset_path=str(MODEL)),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=min_conf,
            min_tracking_confidence=min_conf,
        )
        self._lm = vision.HandLandmarker.create_from_options(opts)
        self._last_ts = 0

    def process(self, bgr: np.ndarray, ts_ms: int) -> list[Hand]:
        ts_ms = max(ts_ms, self._last_ts + 1)  # timestamps strictement croissants
        self._last_ts = ts_ms
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        img = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        res = self._lm.detect_for_video(img, ts_ms)
        hands = []
        for lms, hd in zip(res.hand_landmarks, res.handedness):
            arr = np.array([[p.x, p.y, p.z] for p in lms], dtype=np.float32)
            hands.append(Hand(arr, hd[0].category_name, float(hd[0].score)))
        return hands

    def close(self) -> None:
        self._lm.close()


def draw_hand(frame: np.ndarray, hand: Hand, label: str = "") -> None:
    h, w = frame.shape[:2]
    pts = (hand.landmarks[:, :2] * (w, h)).astype(int)
    for a, b in CONNECTIONS:
        cv2.line(frame, tuple(pts[a]), tuple(pts[b]), (200, 200, 200), 2)
    for p in pts:
        cv2.circle(frame, tuple(p), 4, (30, 140, 255), -1)
    if label:
        x, y = pts[:, 0].min(), max(pts[:, 1].min() - 10, 15)
        cv2.putText(frame, label, (int(x), int(y)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

"""Reconnaissance des 6 gestes classiques par règles géométriques (invariantes à la rotation)."""
from __future__ import annotations

import numpy as np

GESTURES = ["OPEN_PALM", "THUMBS_UP", "PEACE", "FIST", "POINTING", "OK_SIGN"]
TIPS, PIPS = [8, 12, 16, 20], [6, 10, 14, 18]


def _d(a, b) -> float:
    return float(np.linalg.norm(a[:2] - b[:2]))


def finger_states(lm: np.ndarray) -> list[bool]:
    """[pouce, index, majeur, annulaire, auriculaire] : True = étendu."""
    wrist = lm[0]
    fingers = [_d(lm[t], wrist) > _d(lm[p], wrist) * 1.15 for t, p in zip(TIPS, PIPS)]
    thumb = _d(lm[4], lm[17]) > _d(lm[3], lm[17]) * 1.05 and _d(lm[4], lm[5]) > _d(lm[3], lm[5])
    return [thumb] + fingers


def classify(lm: np.ndarray) -> tuple[str | None, float]:
    """Retourne (geste, confiance 0..1) ou (None, 0)."""
    size = max(_d(lm[0], lm[9]), 1e-6)
    th, ix, mi, ri, pi = finger_states(lm)
    pinch = _d(lm[4], lm[8]) / size

    if pinch < 0.30 and mi and ri and pi:
        return "OK_SIGN", float(np.clip(1 - pinch / 0.30 * 0.4, 0.6, 1))
    if th and ix and mi and ri and pi:
        return "OPEN_PALM", 0.9
    if not (ix or mi or ri or pi):
        if th and lm[4][1] < lm[3][1] < lm[5][1] and (lm[0][1] - lm[4][1]) / size > 0.9:
            return "THUMBS_UP", 0.9
        if not th or _d(lm[4], lm[5]) / size < 0.9:
            return "FIST", 0.85
    if ix and not (mi or ri or pi):
        return "POINTING", 0.85
    if ix and mi and not (ri or pi):
        return "PEACE", 0.85
    return None, 0.0

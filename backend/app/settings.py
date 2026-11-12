"""Configuration JSON légère (config/settings.json)."""
from __future__ import annotations

import json
import threading
from pathlib import Path

PATH = Path(__file__).resolve().parents[2] / "config" / "settings.json"

DEFAULTS: dict = {
    "profile": "LITE",          # LITE | ADVANCED
    "camera_source": "webcam",  # webcam | phone (QR code)
    "camera_index": 0,
    "camera_url": "",           # flux téléphone / caméra IP (http, https, rtsp) ; vide = webcam
    "width": 640, "height": 480,
    "simulate": False,
    "max_hands": 1,
    "modules": {"hands": True, "gestures": True, "objects": False},
    "min_confidence": 0.7,
    "cooldown": 1.5,
    "yolo_every_n": 6,
    "yolo_model": "yolov8n.onnx",  # ex. yolov8s.onnx exporté depuis le notebook Colab (plus précis, plus lent)
    "air_mouse": False,         # souris aérienne (nécessite contrôle activé)
    "air_smoothing": 0.5,       # 0 = réactif, 1 = très lissé
    "air_margin": 0.15,         # bord de l'image ignoré : atteindre les coins sans tendre le bras
    "gesture_actions": {
        "OPEN_PALM": "none", "THUMBS_UP": "volume_up", "PEACE": "scroll_up",
        "FIST": "none", "POINTING": "none", "OK_SIGN": "none",
    },
    "custom_actions": {},
}


class Settings:
    def __init__(self):
        self._lock = threading.Lock()
        self.data = json.loads(json.dumps(DEFAULTS))
        if PATH.exists():
            try:
                self._merge(self.data, json.loads(PATH.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                pass

    def _merge(self, base: dict, new: dict) -> None:
        for k, v in new.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict) and k not in ("custom_actions",):
                self._merge(base[k], v)
            else:
                base[k] = v

    def update(self, patch: dict) -> dict:
        with self._lock:
            self._merge(self.data, {k: v for k, v in patch.items() if k in DEFAULTS})
            PATH.parent.mkdir(parents=True, exist_ok=True)
            PATH.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")
            return self.data

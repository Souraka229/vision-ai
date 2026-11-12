"""Télécharge les modèles nécessaires dans backend/models/ (non versionnés dans git)."""
import sys
import urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parents[1] / "backend" / "models"
MODELS = {
    "hand_landmarker.task": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
    # YOLOv8n (poids Ultralytics, licence AGPL-3.0) : requis seulement pour le profil ADVANCED
    "yolov8n.onnx": "https://huggingface.co/unity/inference-engine-yolo/resolve/main/models/yolov8n.onnx",
}


def main(names: list[str]) -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    rc = 0
    for name in names or MODELS:
        out = DEST / name
        if out.exists() and out.stat().st_size > 1_000_000:
            continue
        print(f"Téléchargement de {name}...")
        try:
            urllib.request.urlretrieve(MODELS[name], out)
        except Exception as e:  # noqa: BLE001
            print(f"ÉCHEC {name}: {e}")
            out.unlink(missing_ok=True)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

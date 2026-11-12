"""Gestes personnalisés : dataset, normalisation, Random Forest, évaluation train/test."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split

log = logging.getLogger("gestures.custom")
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "gestures"
MODELS = ROOT / "backend" / "models"


def normalize(lm: np.ndarray, handedness: str = "Right") -> np.ndarray:
    """Translation au poignet, mise à l'échelle par taille de main, miroir main gauche -> 63 valeurs."""
    p = lm.astype(np.float32).copy()
    p -= p[0]
    scale = np.linalg.norm(p[9][:2])
    p /= max(scale, 1e-6)
    if handedness == "Left":
        p[:, 0] *= -1
    return p.flatten()


class CustomGestures:
    def __init__(self, owner: str = "shared"):
        self.owner = owner
        self.dir = DATA / owner
        self.dir.mkdir(parents=True, exist_ok=True)
        self.model_path = MODELS / f"custom_{owner}.joblib"
        self.clf = None
        self.labels: list[str] = []
        self.metrics: dict = {}
        self.load()

    def _file(self, name: str) -> Path:
        safe = "".join(c for c in name if c.isalnum() or c in "_-").upper()
        if not safe:
            raise ValueError("Nom de geste invalide")
        return self.dir / f"{safe}.json"

    def add_sample(self, name: str, lm: np.ndarray, handedness: str) -> int:
        f = self._file(name)
        rows = json.loads(f.read_text()) if f.exists() else []
        rows.append(normalize(lm, handedness).round(5).tolist())
        f.write_text(json.dumps(rows))
        return len(rows)

    def counts(self) -> dict[str, int]:
        return {p.stem: len(json.loads(p.read_text())) for p in sorted(self.dir.glob("*.json"))}

    def delete(self, name: str) -> None:
        self._file(name).unlink(missing_ok=True)

    def train(self) -> dict:
        X, y = [], []
        for p in self.dir.glob("*.json"):
            rows = json.loads(p.read_text())
            X += rows
            y += [p.stem] * len(rows)
        classes = sorted(set(y))
        if len(classes) < 2:
            raise ValueError("Il faut au moins 2 gestes enregistrés")
        if min(y.count(c) for c in classes) < 10:
            raise ValueError("Au moins 10 répétitions par geste sont nécessaires")
        X, y = np.array(X), np.array(y)
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)
        clf = RandomForestClassifier(n_estimators=150, n_jobs=2, random_state=42).fit(Xtr, ytr)
        pred = clf.predict(Xte)
        self.metrics = {
            "accuracy_test": round(float(accuracy_score(yte, pred)), 4),
            "n_train": int(len(ytr)), "n_test": int(len(yte)),
            "labels": list(clf.classes_),
            "confusion_matrix": confusion_matrix(yte, pred, labels=clf.classes_).tolist(),
        }
        # Modèle final réentraîné sur toutes les données ; métriques = évaluées sur le test écarté
        self.clf = RandomForestClassifier(n_estimators=150, n_jobs=2, random_state=42).fit(X, y)
        self.labels = list(self.clf.classes_)
        joblib.dump({"clf": self.clf, "metrics": self.metrics}, self.model_path)
        return self.metrics

    def load(self) -> None:
        if self.model_path.exists():
            d = joblib.load(self.model_path)
            self.clf, self.metrics = d["clf"], d["metrics"]
            self.labels = list(self.clf.classes_)

    def predict(self, lm: np.ndarray, handedness: str) -> tuple[str | None, float]:
        if self.clf is None:
            return None, 0.0
        pr = self.clf.predict_proba([normalize(lm, handedness)])[0]
        i = int(pr.argmax())
        return self.labels[i], float(pr[i])

"""Entraînement avancé des gestes personnalisés (local ou Google Colab).

- séparation train/test AVANT toute augmentation (pas de fuite de données) ;
- augmentation dans l'espace des landmarks (rotation, échelle, bruit) sur le train uniquement ;
- recherche d'hyperparamètres par validation croisée sur le train ;
- sortie compatible avec backend/gestures/custom.py (joblib {"clf", "metrics"}).

Usage : python scripts/train_gestures.py --data data/gestures/shared --out backend/models/custom_shared.joblib
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import GridSearchCV, train_test_split


def load(data: Path) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for p in sorted(data.glob("*.json")):
        rows = json.loads(p.read_text())
        X += rows
        y += [p.stem] * len(rows)
    if len(set(y)) < 2:
        raise SystemExit("Il faut au moins 2 gestes dans " + str(data))
    return np.array(X, dtype=np.float32), np.array(y)


def augment(X: np.ndarray, y: np.ndarray, factor: int, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Rotation 2D (±15°), échelle (±10 %) et bruit gaussien sur des landmarks déjà normalisés (63 valeurs)."""
    rng = np.random.default_rng(seed)
    out_x, out_y = [X], [y]
    for _ in range(factor):
        P = X.reshape(-1, 21, 3).copy()
        a = np.deg2rad(rng.uniform(-15, 15, len(P)))
        c, s = np.cos(a)[:, None], np.sin(a)[:, None]
        x, yy = P[:, :, 0].copy(), P[:, :, 1].copy()
        P[:, :, 0], P[:, :, 1] = c * x - s * yy, s * x + c * yy
        P *= rng.uniform(0.9, 1.1, (len(P), 1, 1))
        P += rng.normal(0, 0.01, P.shape)
        out_x.append(P.reshape(len(P), -1))
        out_y.append(y)
    return np.concatenate(out_x), np.concatenate(out_y)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--augment", type=int, default=4)
    ap.add_argument("--jobs", type=int, default=-1)
    a = ap.parse_args()

    X, y = load(a.data)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=42)
    Xtr_a, ytr_a = augment(Xtr, ytr, a.augment)  # le test reste intact et non augmenté
    grid = GridSearchCV(RandomForestClassifier(random_state=42, n_jobs=1),
                        {"n_estimators": [150, 300], "max_depth": [None, 20], "min_samples_leaf": [1, 2]},
                        cv=3, n_jobs=a.jobs)
    grid.fit(Xtr_a, ytr_a)
    pred = grid.predict(Xte)
    acc = float(accuracy_score(yte, pred))
    print(classification_report(yte, pred, zero_division=0))
    print("meilleurs hyperparamètres :", grid.best_params_)

    # modèle final : mêmes hyperparamètres, toutes les données (train + test, test augmenté exclu des métriques)
    Xall_a, yall_a = augment(X, y, a.augment)
    final = RandomForestClassifier(**grid.best_params_, random_state=42, n_jobs=a.jobs).fit(Xall_a, yall_a)
    metrics = {"accuracy_test": round(acc, 4), "n_train": int(len(ytr)), "n_test": int(len(yte)),
               "labels": list(final.classes_),
               "confusion_matrix": confusion_matrix(yte, pred, labels=final.classes_).tolist(),
               "augment": a.augment, "best_params": grid.best_params_}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"clf": final, "metrics": metrics}, a.out)
    print(f"précision sur test écarté : {acc:.1%} -> modèle sauvegardé dans {a.out}")


if __name__ == "__main__":
    main()

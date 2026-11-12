# VISION AI : la souris sans les mains

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Souraka229/vision-ai/blob/main/notebooks/vision_ai_colab.ipynb)

**Le problème.** Clavier et souris sont inutilisables pour beaucoup de gens : handicap moteur, tendinites et TMS, mains occupées (cuisine, atelier, soins, bricolage). Les solutions existantes sont chères, matérielles, ou demandent un GPU.

**La solution.** VISION AI transforme une simple webcam (ou un téléphone) en souris et en télécommande gestuelle de Windows. Tout tourne **en local, sur CPU** (testé sur un i5 11e gén., 16 Go, sans GPU dédié), sans cloud et sans enregistrer d'images.

## Ce que ça fait

- **Souris aérienne** : la main déplace le curseur (filtre One Euro : stable à l'arrêt, réactif en mouvement).
  Pincer pouce + index = clic · maintenir 0,4 s = glisser-déposer · pouce + majeur = clic droit · deux doigts levés puis monter/descendre = défilement.
- **Gestes personnalisés** : enregistrez vos propres gestes (adaptés à votre mobilité), entraînement Random Forest évalué sur un jeu de test séparé.
- **Gestes prêts à l'emploi** : OPEN_PALM, THUMBS_UP, PEACE, FIST, POINTING, OK_SIGN, chacun lié à une action configurable (volume, raccourcis, scroll...).
- **Téléphone comme caméra** : scannez un QR code, même Wi-Fi, HTTPS local avec jeton à usage unique.
- **Sécurité** : contrôle désactivé par défaut, bouton STOP, liste blanche d'actions (jamais de commande système arbitraire), confirmation des actions sensibles, PIN local.
- **Option ADVANCED** : YOLOv8n (personnes, téléphones...) avec IDs anonymes temporaires. L'indication « téléphone visible » est une estimation visuelle, jamais une affirmation sur l'intention ou l'attention d'une personne.

## Démarrage rapide (Windows)

Prérequis : Python 3.11 et Node.js.

```
git clone https://github.com/Souraka229/vision-ai
cd vision-ai
start.bat
```

`start.bat` crée l'environnement, installe les dépendances, télécharge les modèles, lance le backend (`127.0.0.1:8000`) et le dashboard (`127.0.0.1:5173`). `stop.bat` arrête tout.

**Première utilisation de la souris aérienne** : Computer Control → *Activer* → *Souris aérienne*. Le bouton **STOP** désactive tout immédiatement ; amener le curseur dans un coin de l'écran déclenche aussi l'arrêt de sécurité de PyAutoGUI.

## Puissance max avec Google Colab

Le notebook [`notebooks/vision_ai_colab.ipynb`](notebooks/vision_ai_colab.ipynb) (badge ci-dessus) permet :

1. **GPU gratuit** : exporter un YOLO plus précis (`yolov8s` ou `yolov8m`) en ONNX pour mieux détecter les téléphones. Copiez le fichier dans `backend/models/` et réglez `yolo_model` dans `config/settings.json`.
2. **Entraînement de vos gestes** avec augmentation de données et recherche d'hyperparamètres (`scripts/train_gestures.py`, utilisable aussi en local). Honnêtement, Colab n'apporte ici pas plus de puissance que votre PC (CPU) : l'intérêt est la commodité.

Seuls des fichiers de landmarks (nombres) sont envoyés à Colab, jamais d'images.

## Architecture

`backend/` : `vision` (caméra, MediaPipe, YOLO), `gestures` (règles, custom, stabilisation), `controllers` (Windows, souris aérienne), `identity` (profils PIN), `analytics` (événements SQLite), `api` (FastAPI, WebSocket, appairage téléphone) · `frontend/` : React + TypeScript + Vite + Tailwind · `scripts/` · `tests/` · `docs/TEST_REPORT.md`

## Tests et limites

17 tests automatisés (`pytest tests`). Le détail de ce qui est validé en réel et de ce qui ne l'est pas est dans [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md). Retenez surtout : la souris aérienne est testée par logique et avec un faux pilote, pas encore à l'usage prolongé sur vraie main ; ce n'est pas un dispositif médical.

## Vie privée et licences

Images traitées en mémoire, jamais enregistrées ; pas de reconnaissance faciale ; un geste n'est jamais une preuve d'identité. Code sous licence **MIT**. Les poids YOLOv8 (Ultralytics) sont sous **AGPL-3.0** : ils ne sont pas inclus, ils sont téléchargés à la demande. MediaPipe est sous Apache-2.0.

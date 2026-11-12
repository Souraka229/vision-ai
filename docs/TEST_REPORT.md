# Rapport de tests et de performances

Machine : Windows 11, Intel i5-1135G7 (4 c / 8 t), 15,7 Go RAM, Intel Iris Xe (intégré, non utilisé), webcam intégrée.

## Validé en réel

| Élément | Résultat |
|---|---|
| Python 3.11.9, venv, installation des dépendances, imports | OK |
| Webcam 640×480 (caméra 0) | OK, ~9-10 FPS bruts en faible lumière au 1er test, 30 FPS ensuite |
| MediaPipe Hand Landmarker sur main réelle | OK : FIST et POINTING reconnus en direct |
| YOLOv8n ONNX sur webcam | OK : personne et laptop détectés, IDs anonymes |
| API REST, MJPEG, WebSocket | OK (tests automatisés + usage réel) |
| Frontend : `tsc` + `vite build`, serveur de dev répond 200 | OK |
| `start.bat` : lance backend + frontend, pas de doublon | OK |
| `stop.bat` : ports 8000 et 5173 libérés, aucun process VISION-AI restant | OK |
| 17 tests pytest (dont souris aérienne avec faux pilote : clic, glisser, clic droit, filtre anti-tremblement, relâchement) | 17 passés |

## Performances mesurées

| Profil | FPS | Latence pipeline | RAM backend | CPU backend |
|---|---|---|---|---|
| Python nu | | | 42 Mo | |
| Backend au repos (moteur arrêté) | | | 229 Mo | |
| LITE (mains) en direct | 30,7 | 12,5 ms | 257 Mo | 7,8 % |
| ADVANCED (mains + YOLO 1 passe/6 images) | 23,5 | 24,9 ms | 344 Mo | 18,8 % |

YOLO seul : 124 ms par inférence, +53 Mo. MediaPipe seul : ~26 ms par image au 1er test.

## Non validé en réel (à ne pas considérer comme prouvé)

- Les gestes OPEN_PALM, THUMBS_UP, PEACE, OK_SIGN : testés uniquement sur des mains synthétiques, pas sur une vraie main.
- Détection d'un **téléphone** et « téléphone visible en usage » : logique écrite, non testée avec un vrai téléphone.
- Enregistrement et entraînement d'un geste personnalisé depuis l'interface : l'entraînement est testé en automatique (précision test > 90 % sur données synthétiques), pas encore manuellement.
- Contrôle de l'ordinateur (curseur, clics, volume, raccourcis) : la sécurité (désactivé par défaut, liste blanche, confirmation, STOP) est testée en automatique ; aucune action réelle sur Windows n'a été exécutée.
- Rendu visuel du dashboard : non inspecté par capture d'écran.
- Fonctions non implémentées : caméra IP/RTSP, flux multiples, ByteTrack, OpenVINO (ONNX Runtime CPU utilisé), deux mains non testées.
- Audit GitHub : 4 projets repérés mais non clonés ; licences AGPL/GPL notées dans le README.

## Ajouts récents

| Élément | Statut |
|---|---|
| Appairage téléphone par QR (HTTPS, jeton) | Testé avec un faux téléphone depuis le PC : page servie, jeton valide accepté, mauvais jeton refusé, images reçues. **Pas testé avec un vrai téléphone ni à travers le pare-feu Windows.** |
| Sélection de l'IP Wi-Fi (ignore VPN/virtuel) | Corrigé après constat réel (le VPN ProTUN était choisi) |
| Souris aérienne | Logique testée (faux pilote). **Aucun déplacement ni clic réel sur Windows n'a été exécuté.** |
| Détection « téléphone visible » durcie | Testée sans téléphone (0 faux positif sur 6 s) ; **non testée avec un vrai téléphone** |
| `scripts/train_gestures.py` | Exécuté sur données synthétiques (résultat trivial). Non évalué sur de vraies mains |
| Notebook Colab | JSON valide, cellules locales vérifiées par le script. **Jamais exécuté sur Colab.** |

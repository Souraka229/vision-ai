@echo off
setlocal
cd /d "%~dp0"
title VISION AI

rem --- Evite les doubles instances
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { exit 1 }"
if errorlevel 1 (
  echo VISION AI semble deja lance ^(port 8000 occupe^). Utilisez stop.bat d'abord.
  start "" http://127.0.0.1:5173
  exit /b 0
)

rem --- 1. Python 3.11
set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" --version >nul 2>&1 || ( echo Python 3.11 introuvable. Installez-le : winget install Python.Python.3.11 & pause & exit /b 1 )

rem --- 2. Environnement virtuel
if not exist ".venv\Scripts\python.exe" ( echo Creation de l'environnement virtuel... & "%PY%" -m venv .venv || ( pause & exit /b 1 ) )

rem --- 3. Dependances
.venv\Scripts\python.exe -c "import cv2,mediapipe,sklearn,fastapi,uvicorn,pyautogui,psutil" >nul 2>&1
if errorlevel 1 ( echo Installation des dependances Python... & .venv\Scripts\python.exe -m pip install -r requirements.txt || ( pause & exit /b 1 ) )
if not exist "backend\models\hand_landmarker.task" .venv\Scripts\python.exe scripts\download_models.py hand_landmarker.task
if not exist "backend\models\yolov8n.onnx" .venv\Scripts\python.exe scripts\download_models.py yolov8n.onnx
if not exist "frontend\node_modules" ( echo Installation du frontend... & pushd frontend & call npm install --no-audit --no-fund & popd )

rem --- 4. Backend (local uniquement)
start "VISION-AI backend" /min .venv\Scripts\python.exe -m uvicorn backend.api.server:app --host 127.0.0.1 --port 8000

rem --- 5. Frontend
start "VISION-AI frontend" /min cmd /c "cd frontend && npm run dev"

rem --- 6. Navigateur quand le frontend repond
powershell -NoProfile -Command "for($i=0;$i -lt 40;$i++){ try { Invoke-WebRequest http://127.0.0.1:5173 -UseBasicParsing -TimeoutSec 1 | Out-Null; break } catch { Start-Sleep -Milliseconds 500 } }"
start "" http://127.0.0.1:5173
echo VISION AI demarre : http://127.0.0.1:5173  ^(stop.bat pour arreter^)
endlocal

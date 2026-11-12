"""API FastAPI : REST + flux MJPEG + WebSocket temps réel. Écoute uniquement en local."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.app.engine import Engine
from backend.controllers.computer import ACTIONS
from backend.gestures.rules import GESTURES
from backend.identity.profiles import Profiles
from backend.api.phone import pairing
from backend.vision.camera import Camera
from backend.vision.phone import phone_source

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
app = FastAPI(title="VISION AI")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
engine = Engine()
profiles = Profiles()


class Login(BaseModel):
    name: str
    pin: str


class NewUser(Login):
    role: str = "standard"


class Rec(BaseModel):
    name: str
    target: int = 30


class Act(BaseModel):
    action: str


def user(x_token: str | None = Header(default=None)):
    return profiles.whoami(x_token)


def need_admin(u=Depends(user)):
    if profiles.has_users() and (not u or u["role"] != "admin"):
        raise HTTPException(403, "Droits administrateur requis")
    return u


@app.get("/api/status")
def status():
    return {"running": engine.running, "simulate": engine.camera.simulate if engine.camera else None,
            "error": engine.last_error, "metrics": engine.metrics, "state": engine.state,
            "control": {"enabled": engine.control.enabled, "pending": engine.control.pending_confirm},
            "settings": engine.settings.data, "recording": engine.recording,
            "custom": engine.custom.counts(), "model": engine.custom.metrics,
            "phone": {"active": pairing.active, "connected": phone_source.connected},
            "events": engine.store.recent[:15]}


@app.get("/api/cameras")
def cameras():
    return {"cameras": Camera.list_cameras() if not engine.running else [engine.settings.data["camera_index"]]}


@app.post("/api/phone/pair")
def phone_pair(_=Depends(need_admin)):
    """Ouvre l'appairage : QR code + serveur HTTPS local (fermé par /api/phone/unpair)."""
    return pairing.start()


@app.get("/api/phone")
def phone_info():
    return pairing.info()


@app.post("/api/phone/unpair")
def phone_unpair():
    pairing.stop()
    return {"ok": True}


@app.post("/api/engine/start")
def start():
    if not engine.start():
        raise HTTPException(503, engine.last_error or "Démarrage impossible")
    return {"ok": True}


@app.post("/api/engine/stop")
def stop():
    engine.stop()
    return {"ok": True}


@app.post("/api/settings")
def settings(patch: dict, _=Depends(need_admin)):
    if "profile" in patch:  # profils prédéfinis
        patch["modules"] = {"objects": patch["profile"] == "ADVANCED"} | patch.get("modules", {})
    return engine.settings.update(patch)


@app.get("/api/gestures")
def gestures():
    return {"builtin": GESTURES, "custom": list(engine.custom.counts()), "actions": ACTIONS}


@app.post("/api/gestures/record")
def record(r: Rec):
    if not engine.running:
        raise HTTPException(409, "Démarrez la caméra d'abord")
    engine.recording = {"name": r.name, "target": min(max(r.target, 10), 200), "count": 0}
    return {"ok": True}


@app.post("/api/gestures/train")
def train():
    try:
        return engine.custom.train()
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.delete("/api/gestures/{name}")
def delete_gesture(name: str):
    engine.custom.delete(name)
    return {"ok": True}


@app.post("/api/control/enable")
def control_enable(_=Depends(need_admin)):
    engine.control.enable()
    return {"enabled": True}


@app.post("/api/control/stop")
def control_stop():
    engine.control.stop()
    return {"enabled": False}


@app.post("/api/control/confirm")
def control_confirm():
    return {"result": engine.control.confirm()}


@app.post("/api/control/test")
def control_test(a: Act):
    res = engine.control.execute(a.action)
    if res == "executed":
        engine.store.log("command", a.action)
    return {"result": res}


@app.get("/api/analytics")
def analytics():
    return engine.store.stats()


@app.delete("/api/analytics")
def analytics_clear(_=Depends(need_admin)):
    engine.store.clear()
    return {"ok": True}


@app.get("/api/users")
def users():
    return {"users": profiles.list(), "setup_needed": not profiles.has_users()}


@app.post("/api/users")
def create_user(u: NewUser, me=Depends(user)):
    if profiles.has_users() and (not me or me["role"] != "admin"):
        raise HTTPException(403, "Droits administrateur requis")
    try:
        profiles.create(u.name, u.role if profiles.has_users() else "admin", u.pin)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, str(e))
    return {"ok": True}


@app.post("/api/login")
def login(l: Login):
    try:
        t = profiles.login(l.name, l.pin)
    except PermissionError as e:
        raise HTTPException(429, str(e))
    if not t:
        raise HTTPException(401, "Nom ou PIN incorrect")
    return {"token": t, "user": profiles.whoami(t)}


@app.get("/api/me")
def me(u=Depends(user)):
    return {"user": u}


@app.get("/stream.mjpg")
async def stream():
    async def gen():
        while engine.running:
            j = engine.jpeg()
            if j:
                yield b"--f\r\nContent-Type: image/jpeg\r\n\r\n" + j + b"\r\n"
            await asyncio.sleep(0.04)
    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=f")


@app.websocket("/ws")
async def ws(sock: WebSocket):
    await sock.accept()
    try:
        while True:
            await sock.send_json(status())
            await asyncio.sleep(0.2)
    except (WebSocketDisconnect, RuntimeError):
        pass


@app.on_event("shutdown")
def shutdown():
    pairing.stop()
    engine.stop()

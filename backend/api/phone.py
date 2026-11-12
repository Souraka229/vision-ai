"""Appairage téléphone par QR code.

Un serveur HTTPS séparé (port 8443) n'écoute sur le réseau local que pendant l'appairage.
Le QR contient un jeton aléatoire ; sans lui, aucune image n'est acceptée.
"""
from __future__ import annotations

import datetime as dt
import ipaddress
import logging
import secrets
import socket
import threading
from pathlib import Path

import segno
import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from backend.vision.phone import phone_source

log = logging.getLogger("api.phone")
PORT = 8443
CERT_DIR = Path(__file__).resolve().parents[2] / "data" / "phone"

PAGE = """<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>VISION AI - Caméra</title>
<style>body{margin:0;background:#08080a;color:#fff;font-family:system-ui;text-align:center;padding:16px}
button{background:#ff7a1a;border:0;border-radius:10px;padding:14px 22px;font-size:17px;font-weight:600}
video{width:100%;max-width:480px;border-radius:12px;margin-top:12px}#s{margin-top:10px;color:#aaa}</style></head><body>
<h2>VISION AI</h2><p>Ce téléphone devient la caméra du PC.<br>Les images ne quittent pas votre réseau.</p>
<button id="b">Démarrer la caméra</button><div id="s"></div><video id="v" playsinline muted></video>
<script>
const t=new URLSearchParams(location.search).get("t"),s=document.getElementById("s"),v=document.getElementById("v");
document.getElementById("b").onclick=async()=>{
 try{
  const st=await navigator.mediaDevices.getUserMedia({video:{facingMode:"environment",width:{ideal:640},height:{ideal:480}},audio:false});
  v.srcObject=st;await v.play();
  const ws=new WebSocket("wss://"+location.host+"/phone/ws?t="+encodeURIComponent(t));ws.binaryType="arraybuffer";
  const c=document.createElement("canvas"),x=c.getContext("2d");let n=0;
  ws.onopen=()=>{s.textContent="Connecté au PC. Gardez cette page ouverte.";
   const tick=()=>{ if(ws.readyState!==1)return; if(ws.bufferedAmount<200000&&v.videoWidth){
     c.width=640;c.height=Math.round(640*v.videoHeight/v.videoWidth);x.drawImage(v,0,0,c.width,c.height);
     c.toBlob(b=>b&&ws.readyState===1&&ws.send(b),"image/jpeg",0.6);n++;}
     setTimeout(tick,66);};tick();};
  ws.onclose=()=>{s.textContent="Déconnecté (jeton invalide ou appairage terminé).";};
 }catch(e){s.textContent="Erreur caméra : "+e.message;}
};
</script></body></html>"""


_SKIP = ("tun", "tap", "vpn", "vethernet", "virtual", "vmware", "vbox", "bluetooth", "loopback", "docker", "wsl", "hyper-v")


def lan_ip() -> str:
    """IP de l'interface Wi-Fi/Ethernet réelle (ignore VPN, réseaux virtuels et 169.254.x.x)."""
    import psutil
    cands = []
    for name, addrs in psutil.net_if_addrs().items():
        low = name.lower()
        if any(k in low for k in _SKIP):
            continue
        for a in addrs:
            if a.family == socket.AF_INET and not a.address.startswith(("169.254.", "127.")):
                rank = 0 if any(k in low for k in ("wi-fi", "wifi", "wlan", "wireless")) else 1
                cands.append((rank, a.address))
    if cands:
        return sorted(cands)[0][1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # aucun paquet envoyé : sert à choisir l'interface locale
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def _make_cert(ip: str) -> tuple[Path, Path]:
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "VISION AI local")])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now)
            .not_valid_after(now + dt.timedelta(days=30))
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address(ip))]), False)
            .sign(key, hashes.SHA256()))
    kp, cp = CERT_DIR / "key.pem", CERT_DIR / "cert.pem"
    kp.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                                     serialization.NoEncryption()))
    cp.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    return kp, cp


class PhonePairing:
    def __init__(self):
        self.token: str | None = None
        self.url: str | None = None
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self.app = self._build_app()

    @property
    def active(self) -> bool:
        return self.token is not None

    def _build_app(self) -> FastAPI:
        app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

        @app.get("/phone", response_class=HTMLResponse)
        def page():
            return PAGE

        @app.websocket("/phone/ws")
        async def ws(sock: WebSocket, t: str = ""):
            if not self.token or not secrets.compare_digest(t, self.token):
                await sock.close(code=1008)
                return
            await sock.accept()
            try:
                while self.token:
                    data = await sock.receive_bytes()
                    if len(data) < 1_000_000:  # limite de taille d'une image
                        phone_source.push(data)
            except (WebSocketDisconnect, RuntimeError):
                pass

        return app

    def start(self) -> dict:
        if self.active:
            return self.info()
        ip = lan_ip()
        key, cert = _make_cert(ip)
        self.token = secrets.token_urlsafe(9)
        self.url = f"https://{ip}:{PORT}/phone?t={self.token}"
        cfg = uvicorn.Config(self.app, host="0.0.0.0", port=PORT, ssl_keyfile=str(key), ssl_certfile=str(cert),
                             log_level="warning")
        self._server = uvicorn.Server(cfg)
        self._thread = threading.Thread(target=self._server.run, daemon=True, name="phone-https")
        self._thread.start()
        log.warning("Appairage téléphone ouvert sur %s:%d", ip, PORT)
        return self.info()

    def stop(self) -> None:
        self.token = self.url = None
        if self._server:
            self._server.should_exit = True
        self._server = self._thread = None
        log.warning("Appairage téléphone fermé")

    def info(self) -> dict:
        qr = segno.make(self.url, error="m").svg_inline(scale=6, dark="#000", light="#fff", border=2) if self.url else None
        return {"active": self.active, "url": self.url, "qr_svg": qr, "connected": phone_source.connected}


pairing = PhonePairing()

import sys
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.controllers.computer import ComputerController  # noqa: E402
from backend.gestures import custom as custom_mod  # noqa: E402
from backend.gestures.rules import classify  # noqa: E402
from backend.gestures.stabilizer import Stabilizer  # noqa: E402


def hand(ext, thumb_up=False, pinch=False):
    """Main synthétique (poignet en bas, doigts vers le haut). ext = [index, majeur, annulaire, auriculaire]."""
    lm = np.zeros((21, 3), np.float32)
    lm[0] = (0.5, 0.9, 0)
    xs = [0.40, 0.47, 0.54, 0.61]
    for f, (x, e) in enumerate(zip(xs, ext)):
        b = 5 + 4 * f
        lm[b] = (x, 0.65, 0)
        if e:
            lm[b + 1], lm[b + 2], lm[b + 3] = (x, 0.55, 0), (x, 0.45, 0), (x, 0.35, 0)
        else:
            lm[b + 1], lm[b + 2], lm[b + 3] = (x, 0.58, 0), (x, 0.66, 0), (x, 0.72, 0)
    lm[1], lm[2], lm[3] = (0.43, 0.82, 0), (0.38, 0.74, 0), (0.34, 0.68, 0)
    lm[4] = (0.30, 0.62, 0)
    if thumb_up:
        lm[1], lm[2], lm[3], lm[4] = (0.45, 0.82, 0), (0.43, 0.70, 0), (0.42, 0.58, 0), (0.42, 0.45, 0)
    elif not any(ext):
        lm[3], lm[4] = (0.47, 0.70, 0), (0.46, 0.68, 0)
    if pinch:
        lm[4] = lm[8] + (0.01, 0.01, 0)
    return lm


def test_open_palm():
    assert classify(hand([1, 1, 1, 1]))[0] == "OPEN_PALM"


def test_fist():
    assert classify(hand([0, 0, 0, 0]))[0] == "FIST"


def test_pointing():
    assert classify(hand([1, 0, 0, 0]))[0] == "POINTING"


def test_peace():
    assert classify(hand([1, 1, 0, 0]))[0] == "PEACE"


def test_thumbs_up():
    assert classify(hand([0, 0, 0, 0], thumb_up=True))[0] == "THUMBS_UP"


def test_ok_sign():
    lm = hand([1, 1, 1, 1])
    lm[8] = (0.40, 0.45, 0)
    lm[7], lm[6] = (0.40, 0.5, 0), (0.40, 0.58, 0)
    lm[4] = lm[8] + (0.01, 0.01, 0)
    assert classify(lm)[0] == "OK_SIGN"


def test_stabilizer_cooldown():
    s = Stabilizer(window=4, min_votes=3, cooldown=10, min_conf=0.5)
    fires = 0
    for _ in range(3):
        for _ in range(5):
            _, f = s.update("FIST", 0.9)
            fires += f
        for _ in range(5):
            s.update(None, 0)
    assert fires == 1  # cooldown : un seul déclenchement


def test_stabilizer_ignores_noise():
    s = Stabilizer(window=6, min_votes=5)
    fires = sum(s.update(g, 0.9)[1] for g in ["FIST", "PEACE", "FIST", "OPEN_PALM", "FIST", "PEACE"])
    assert fires == 0


def test_control_disabled_by_default():
    c = ComputerController()
    assert c.enabled is False
    assert c.execute("left_click") == "ignored:disabled"


def test_control_rejects_unknown_and_requires_confirm():
    c = ComputerController()
    c.enabled = True
    assert c.execute("rm -rf /") == "ignored:unknown"
    assert c.execute("hotkey:show_desktop") == "confirm_required"
    assert c.pending_confirm == "hotkey:show_desktop"
    c.stop()
    assert c.enabled is False and c.pending_confirm is None


def test_custom_training_with_held_out_test(tmp_path, monkeypatch):
    monkeypatch.setattr(custom_mod, "DATA", tmp_path / "d")
    monkeypatch.setattr(custom_mod, "MODELS", tmp_path)
    cg = custom_mod.CustomGestures("t")
    rng = np.random.default_rng(0)
    for name, ext in {"ALPHA": [1, 0, 0, 0], "BETA": [1, 1, 1, 1]}.items():
        for _ in range(40):
            cg.add_sample(name, hand(ext) + rng.normal(0, 0.005, (21, 3)).astype(np.float32), "Right")
    m = cg.train()
    assert m["n_test"] > 0 and m["accuracy_test"] > 0.9
    assert cg.predict(hand([1, 0, 0, 0]), "Right")[0] == "ALPHA"
    assert custom_mod.CustomGestures("t").clf is not None  # rechargé depuis le disque


def test_train_refuses_too_few_samples(tmp_path, monkeypatch):
    monkeypatch.setattr(custom_mod, "DATA", tmp_path / "d2")
    monkeypatch.setattr(custom_mod, "MODELS", tmp_path)
    cg = custom_mod.CustomGestures("x")
    cg.add_sample("A", hand([1, 0, 0, 0]), "Right")
    with pytest.raises(ValueError):
        cg.train()


def test_api_simulation_and_websocket(tmp_path):
    from fastapi.testclient import TestClient
    from backend.api import server
    c = TestClient(server.app)
    server.engine.settings.data["simulate"] = True
    assert c.get("/api/status").json()["control"]["enabled"] is False
    assert c.post("/api/engine/start").status_code == 200
    time.sleep(1.5)
    st = c.get("/api/status").json()
    assert st["running"] and st["simulate"] is True
    with c.websocket_connect("/ws") as ws:
        assert "metrics" in ws.receive_json()
    assert c.post("/api/engine/stop").status_code == 200
    assert c.get("/api/status").json()["running"] is False
    server.engine.settings.data["simulate"] = False


# ---------- souris aérienne ----------
class FakeControl:
    def __init__(self):
        self.log = []

    def move_cursor(self, x, y, m=0.15): self.log.append(("move",))
    def click(self, b="left"): self.log.append(("click", b))
    def mouse_down(self): self.log.append(("down",))
    def mouse_up(self): self.log.append(("up",))
    def scroll(self, n): self.log.append(("scroll", n))


def _pinched(kind):
    lm = hand([1, 1, 1, 1])
    if kind == "index":
        lm[8] = lm[4] + (0.005, 0.005, 0)
    elif kind == "middle":
        lm[12] = lm[4] + (0.005, 0.005, 0)
    return lm


def test_airmouse_pinch_click_and_drag():
    from backend.controllers.airmouse import AirMouse
    c = FakeControl()
    m = AirMouse(c)
    m.update(hand([1, 1, 1, 1]), "OPEN_PALM", 0.0)
    m.update(_pinched("index"), None, 0.1)            # début du pincement
    m.update(hand([1, 1, 1, 1]), "OPEN_PALM", 0.25)   # relâché vite -> clic
    assert ("click", "left") in c.log and ("down",) not in c.log
    c.log.clear()
    m.update(_pinched("index"), None, 1.0)
    m.update(_pinched("index"), None, 1.5)            # maintenu > 0,4 s -> glisser
    m.update(hand([1, 1, 1, 1]), "OPEN_PALM", 1.8)    # relâché -> dépôt
    assert [e[0] for e in c.log if e[0] in ("down", "up", "click")] == ["down", "up"]


def test_airmouse_right_click_cooldown():
    from backend.controllers.airmouse import AirMouse
    c = FakeControl()
    m = AirMouse(c)
    m.update(_pinched("middle"), None, 0.0)
    m.update(_pinched("middle"), None, 0.2)
    assert c.log.count(("click", "right")) == 1


def test_airmouse_filter_reduces_jitter():
    import numpy as np
    from backend.controllers.airmouse import OneEuro
    f = OneEuro(min_cutoff=0.8)
    rng = np.random.default_rng(1)
    raw = [np.array([0.5, 0.5]) + rng.normal(0, 0.004, 2) for _ in range(60)]
    out = [f(p, i / 30) for i, p in enumerate(raw)]
    assert np.std([o[0] for o in out[20:]]) < 0.5 * np.std([r[0] for r in raw[20:]])


def test_airmouse_release_drops_button():
    from backend.controllers.airmouse import AirMouse
    c = FakeControl()
    m = AirMouse(c)
    m.update(_pinched("index"), None, 0.0)
    m.update(_pinched("index"), None, 0.6)
    m.release()
    assert c.log[-1] == ("up",)

"""Souris aérienne : le pointeur suit la main, le pincement clique, le maintien glisse.

Conçu pour l'accessibilité (clavier/souris difficiles à utiliser) :
- pointeur sur l'articulation du majeur (9), qui bouge peu quand on pince -> pas de saut au clic ;
- filtre One Euro : stable à l'arrêt, réactif en mouvement ;
- pincement pouce+index = clic gauche, maintenu 0,4 s = glisser-déposer ;
- pincement pouce+majeur = clic droit ; deux doigts levés (PEACE) + mouvement vertical = défilement.
"""
from __future__ import annotations

import math
import time

import numpy as np


class OneEuro:
    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.02, d_cutoff: float = 1.0):
        self.min_cutoff, self.beta, self.d_cutoff = min_cutoff, beta, d_cutoff
        self.x: np.ndarray | None = None
        self.dx = np.zeros(2)
        self.t = 0.0

    @staticmethod
    def _alpha(cutoff: float, dt: float) -> float:
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def __call__(self, p: np.ndarray, t: float) -> np.ndarray:
        if self.x is None:
            self.x, self.t = p.copy(), t
            return p
        dt = max(t - self.t, 1e-3)
        dx = (p - self.x) / dt
        self.dx += self._alpha(self.d_cutoff, dt) * (dx - self.dx)
        cutoff = self.min_cutoff + self.beta * float(np.linalg.norm(self.dx))
        self.x = self.x + self._alpha(cutoff, dt) * (p - self.x)
        self.t = t
        return self.x

    def reset(self) -> None:
        self.x = None


def _d(a, b) -> float:
    return float(np.linalg.norm(a[:2] - b[:2]))


class AirMouse:
    PINCH_ON, PINCH_OFF = 0.28, 0.40      # hystérésis (fraction de la taille de main)
    HOLD_TO_DRAG = 0.4                     # secondes
    RIGHT_COOLDOWN = 0.8

    def __init__(self, control):
        self.control = control
        self.f = OneEuro()
        self.pinching = False
        self.pinch_t = 0.0
        self.dragging = False
        self.last_right = -1e9
        self.last_scroll_y: float | None = None
        self.last: dict = {}

    BASE_GAIN = 2.8   # traverser l'écran en bougeant la main sur ~36 % de la largeur de l'image
    mode = "relative"
    speed = 1.0
    margin = 0.15
    screen_w = 1920.0
    prev: np.ndarray | None = None
    prev_t = 0.0

    def configure(self, smoothing: float, margin: float, mode: str = "relative", speed: float = 1.0) -> None:
        # 0 = très réactif, 1 = très lissé ; beta élevé : le filtre lâche prise dès que la main accélère
        self.f.min_cutoff = float(np.interp(smoothing, [0, 1], [4.0, 0.8]))
        self.f.beta = 0.08
        self.margin, self.mode, self.speed = margin, mode, float(speed)

    def release(self) -> None:
        if self.dragging:
            self.control.mouse_up()
        self.pinching = self.dragging = False
        self.last_scroll_y = None
        self.prev = None  # la main revient : pas de saut du curseur
        self.f.reset()

    def update(self, lm: np.ndarray, gesture: str | None, now: float | None = None) -> dict:
        """Traite une main. Retourne les actions effectuées (pour les tests et les stats)."""
        now = time.time() if now is None else now
        out: dict = {}
        size = max(_d(lm[0], lm[9]), 1e-6)
        idx_pinch = _d(lm[4], lm[8]) / size
        mid_pinch = _d(lm[4], lm[12]) / size

        # pointeur : moyenne des 3 articulations de base des doigts (stable quand on pince)
        raw = (lm[5][:2] + lm[9][:2] + lm[13][:2]) / 3.0
        p = self.f(raw.astype(float), now)
        if self.mode == "absolute":
            self.control.move_cursor(float(p[0]), float(p[1]), self.margin, smooth=1.0)
            out["move"] = True
        else:
            dt = max(now - self.prev_t, 1e-3) if self.prev is not None else 1.0
            delta = (p - self.prev) if self.prev is not None else np.zeros(2)
            self.prev, self.prev_t = p.copy(), now
            clutch = gesture == "FIST"                                   # poing = on « soulève la souris »
            freeze = self.pinching and not self.dragging                 # le clic atterrit où on a visé
            if not clutch and not freeze and dt < 0.3:
                speed = float(np.linalg.norm(delta)) / dt                # unités d'image / seconde
                accel = 0.6 + 1.2 * min(speed / 0.6, 1.0)                # lent = précis (0,6x), rapide = 1,8x
                gain = self.BASE_GAIN * self.speed * accel
                self.control.move_relative(-delta[0] * gain * self.screen_w, delta[1] * gain * self.screen_w)
                out["move"] = True
            out["clutch"] = clutch

        # défilement : deux doigts levés, déplacement vertical
        if gesture == "PEACE":
            if self.last_scroll_y is not None:
                dy = lm[9][1] - self.last_scroll_y
                if abs(dy) > 0.004:
                    self.control.scroll(int(-dy * 4000))
                    out["scroll"] = dy
            self.last_scroll_y = float(lm[9][1])
        else:
            self.last_scroll_y = None

        # clic gauche / glisser (pincement pouce + index)
        if not self.pinching and idx_pinch < self.PINCH_ON and mid_pinch > self.PINCH_OFF:
            self.pinching, self.pinch_t = True, now
        elif self.pinching:
            held = now - self.pinch_t
            if idx_pinch > self.PINCH_OFF:  # relâché
                if self.dragging:
                    self.control.mouse_up()
                    out["drop"] = True
                elif held < self.HOLD_TO_DRAG:
                    self.control.click("left")
                    out["click"] = "left"
                self.pinching = self.dragging = False
            elif held >= self.HOLD_TO_DRAG and not self.dragging:
                self.control.mouse_down()
                self.dragging = True
                out["drag"] = True

        # clic droit (pouce + majeur)
        if not self.pinching and mid_pinch < self.PINCH_ON and idx_pinch > self.PINCH_OFF \
                and now - self.last_right > self.RIGHT_COOLDOWN:
            self.control.click("right")
            self.last_right = now
            out["click"] = "right"
        self.last = out
        return out

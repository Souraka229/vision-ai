"""Stabilisation temporelle + cooldown pour éviter les déclenchements répétés."""
from __future__ import annotations

import time
from collections import deque


class Stabilizer:
    def __init__(self, window: int = 6, min_votes: int = 5, cooldown: float = 1.5, min_conf: float = 0.7):
        self.window, self.min_votes, self.cooldown, self.min_conf = window, min_votes, cooldown, min_conf
        self.hist: deque = deque(maxlen=window)
        self.stable: str | None = None
        self._last_fire: dict[str, float] = {}

    def update(self, gesture: str | None, conf: float) -> tuple[str | None, bool]:
        """Retourne (geste stable, déclenchement ?). Déclenche une fois à l'entrée dans le geste."""
        self.hist.append(gesture if gesture and conf >= self.min_conf else None)
        cand = None
        if len(self.hist) == self.window:
            for g in set(self.hist):
                if g and self.hist.count(g) >= self.min_votes:
                    cand = g
        fire = False
        if cand != self.stable:
            self.stable = cand
            now = time.time()
            if cand and now - self._last_fire.get(cand, 0) >= self.cooldown:
                self._last_fire[cand] = now
                fire = True
        return self.stable, fire

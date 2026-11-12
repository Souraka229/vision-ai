"""Contrôle Windows sécurisé : désactivé par défaut, whitelist d'actions, STOP immédiat."""
from __future__ import annotations

import logging
import time

log = logging.getLogger("controllers.computer")

# Raccourcis autorisés uniquement (jamais de commande système arbitraire)
ALLOWED_HOTKEYS = {
    "copy": ("ctrl", "c"), "paste": ("ctrl", "v"), "undo": ("ctrl", "z"),
    "next_tab": ("ctrl", "tab"), "prev_tab": ("ctrl", "shift", "tab"),
    "alt_tab": ("alt", "tab"), "show_desktop": ("win", "d"), "play_pause": ("playpause",),
    "next_track": ("nexttrack",), "screenshot": ("win", "shift", "s"),
}
SENSITIVE = {"show_desktop", "alt_tab", "screenshot"}
ACTIONS = ["none", "left_click", "right_click", "scroll_up", "scroll_down", "volume_up",
           "volume_down", "mute", "hotkey:copy", "hotkey:paste", "hotkey:undo", "hotkey:next_tab",
           "hotkey:prev_tab", "hotkey:alt_tab", "hotkey:show_desktop", "hotkey:play_pause",
           "hotkey:next_track", "hotkey:screenshot"]


class ComputerController:
    def __init__(self):
        self.enabled = False
        self.pending_confirm: str | None = None  # action sensible en attente
        self.dragging = False
        self._pg = None
        self._smooth = None

    def _gui(self):
        if self._pg is None:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0
            self._pg = pyautogui
        return self._pg

    def enable(self) -> None:
        self.enabled = True
        log.warning("Contrôle ordinateur ACTIVÉ")

    def stop(self) -> None:
        """STOP d'urgence : désactive tout et relâche le bouton si drag en cours."""
        self.enabled = False
        self.pending_confirm = None
        if self.dragging and self._pg:
            self._pg.mouseUp()
        self.dragging = False
        self._smooth = None
        log.warning("Contrôle ordinateur STOPPÉ")

    def move_cursor(self, nx: float, ny: float, margin: float = 0.15) -> None:
        """nx, ny normalisés (0..1, image non miroir). Zone active réduite + lissage."""
        if not self.enabled:
            return
        pg = self._gui()
        w, h = pg.size()
        x = min(max((1 - nx - margin) / (1 - 2 * margin), 0), 1) * (w - 1)  # miroir horizontal
        y = min(max((ny - margin) / (1 - 2 * margin), 0), 1) * (h - 1)
        if self._smooth is None:
            self._smooth = (x, y)
        sx, sy = self._smooth
        self._smooth = (sx + (x - sx) * 0.35, sy + (y - sy) * 0.35)
        pg.moveTo(*self._smooth)

    # primitives utilisées par la souris aérienne (soumises au même interrupteur enabled)
    def click(self, button: str = "left") -> None:
        if self.enabled and button in ("left", "right"):
            self._gui().click(button=button)

    def mouse_down(self) -> None:
        if self.enabled:
            self._gui().mouseDown()
            self.dragging = True

    def mouse_up(self) -> None:
        if self._pg and self.dragging:
            self._pg.mouseUp()
        self.dragging = False

    def scroll(self, amount: int) -> None:
        if self.enabled:
            self._gui().scroll(max(-600, min(600, amount)))

    def drag(self, start: bool) -> None:
        if not self.enabled:
            return
        pg = self._gui()
        if start and not self.dragging:
            pg.mouseDown()
            self.dragging = True
        elif not start and self.dragging:
            pg.mouseUp()
            self.dragging = False

    def execute(self, action: str, confirmed: bool = False) -> str:
        """Exécute une action de la whitelist. Retourne un statut lisible."""
        if not self.enabled:
            return "ignored:disabled"
        if action not in ACTIONS or action == "none":
            return "ignored:unknown"
        if action.startswith("hotkey:") and action[7:] in SENSITIVE and not confirmed:
            self.pending_confirm = action
            return "confirm_required"
        pg = self._gui()
        if action == "left_click":
            pg.click()
        elif action == "right_click":
            pg.click(button="right")
        elif action == "scroll_up":
            pg.scroll(300)
        elif action == "scroll_down":
            pg.scroll(-300)
        elif action in ("volume_up", "volume_down", "mute"):
            pg.press({"volume_up": "volumeup", "volume_down": "volumedown", "mute": "volumemute"}[action])
        elif action.startswith("hotkey:"):
            pg.hotkey(*ALLOWED_HOTKEYS[action[7:]])
        self.pending_confirm = None
        log.info("action exécutée: %s", action)
        return "executed"

    def confirm(self) -> str:
        a, self.pending_confirm = self.pending_confirm, None
        return self.execute(a, confirmed=True) if a else "ignored:nothing_pending"

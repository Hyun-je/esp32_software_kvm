"""
Minimal status window — three LED indicators for ESP32, BLE, and forwarding state.
Uses only tkinter (stdlib), no extra dependencies required.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

_GREEN = "#4CAF50"
_RED   = "#F44336"
_GRAY  = "#424242"

_BG    = "#1C1C1C"
_FG    = "#888888"

_INDICATORS = [
    ("esp32", "ESP32"),
    ("ble",   "BLE"),
    ("fwd",   "FWD"),
]


class StatusWindow:
    """Small always-on-top window showing three LED-style status indicators."""

    def __init__(self, on_close: Callable | None = None) -> None:
        root = tk.Tk()
        root.title("KVM")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg=_BG)

        if on_close:
            root.protocol("WM_DELETE_WINDOW", on_close)

        frame = tk.Frame(root, bg=_BG, padx=12, pady=10)
        frame.pack()

        self._root = root
        self._leds: dict[str, tuple[tk.Canvas, int]] = {}

        for col_idx, (key, label) in enumerate(_INDICATORS):
            col = tk.Frame(frame, bg=_BG)
            col.grid(row=0, column=col_idx, padx=10)

            canvas = tk.Canvas(col, width=20, height=20, bg=_BG, highlightthickness=0)
            canvas.pack()
            oval = canvas.create_oval(2, 2, 18, 18, fill=_GRAY, outline="")

            tk.Label(col, text=label, fg=_FG, bg=_BG, font=("Helvetica", 9)).pack()

            self._leds[key] = (canvas, oval)

    # ------------------------------------------------------------------
    # Thread-safe state setters (safe to call from any thread)
    # ------------------------------------------------------------------

    def set_esp32(self, connected: bool) -> None:
        self._root.after(0, self._set_color, "esp32", _GREEN if connected else _RED)

    def set_ble(self, connected: bool) -> None:
        self._root.after(0, self._set_color, "ble", _GREEN if connected else _RED)

    def set_forwarding(self, enabled: bool) -> None:
        self._root.after(0, self._set_color, "fwd", _GREEN if enabled else _GRAY)

    def after(self, ms: int, func: Callable) -> None:
        """Schedule func to run on the GUI thread after ms milliseconds."""
        self._root.after(ms, func)

    def run(self) -> None:
        """Start the tkinter event loop (blocks until the window is closed)."""
        self._root.mainloop()

    def close(self) -> None:
        try:
            self._root.quit()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _set_color(self, key: str, color: str) -> None:
        canvas, oval = self._leds[key]
        canvas.itemconfig(oval, fill=color)

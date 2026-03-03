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

    def __init__(self) -> None:
        root = tk.Tk()
        root.overrideredirect(True)   # remove title bar and close button
        root.configure(bg=_BG)

        frame = tk.Frame(root, bg=_BG, padx=12, pady=10)
        frame.pack()

        # Allow dragging the borderless window
        self._drag_x = 0
        self._drag_y = 0

        def _on_drag_start(event: tk.Event) -> None:
            self._drag_x = event.x_root - root.winfo_x()
            self._drag_y = event.y_root - root.winfo_y()

        def _on_drag_move(event: tk.Event) -> None:
            root.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

        root.bind("<ButtonPress-1>", _on_drag_start)
        root.bind("<B1-Motion>", _on_drag_move)

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

    def set_ble(self, connected: bool | None) -> None:
        """None = unknown (gray), True = connected (green), False = disconnected (red)."""
        if connected is True:
            color = _GREEN
        elif connected is False:
            color = _RED
        else:
            color = _GRAY
        self._root.after(0, self._set_color, "ble", color)

    def set_forwarding(self, enabled: bool) -> None:
        self._root.after(0, self._set_color, "fwd", _GREEN if enabled else _GRAY)

    def after(self, ms: int, func: Callable) -> None:
        """Schedule func to run on the GUI thread after ms milliseconds."""
        self._root.after(ms, func)

    def run(self) -> None:
        """Start the tkinter event loop (blocks until the window is closed)."""
        # Position at bottom-right corner before entering the event loop
        self._root.update_idletasks()
        margin_x = 16
        margin_y = 64
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        sw = self._root.winfo_screenwidth()
        sh = self._root.winfo_screenheight()
        self._root.geometry(f"+{sw - w - margin_x}+{sh - h - margin_y}")
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

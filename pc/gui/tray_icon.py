"""
System tray icon for Windows — drop-in replacement for StatusWindow.

Requires: pystray>=0.19  Pillow>=9.0
    pip install pystray Pillow
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

import pystray
from PIL import Image, ImageDraw

_GREEN  = (76, 175, 80)
_YELLOW = (255, 193, 7)
_RED    = (244, 67, 54)

_ICON_SIZE = 64
_MARGIN    = 6


def _circle_color(esp32: bool, ble, forwarding: bool):
    if esp32 and ble is True:
        return _GREEN if forwarding else _YELLOW
    return _RED


def _make_image(esp32: bool, ble, forwarding: bool) -> Image.Image:
    img  = Image.new("RGBA", (_ICON_SIZE, _ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = _circle_color(esp32, ble, forwarding)
    draw.ellipse(
        [_MARGIN, _MARGIN, _ICON_SIZE - _MARGIN, _ICON_SIZE - _MARGIN],
        fill=color,
    )
    return img


def _make_title(esp32: bool, ble, forwarding: bool) -> str:
    e = "Y" if esp32 else "N"
    b = "Y" if ble is True else ("N" if ble is False else "?")
    f = "ON" if forwarding else "OFF"
    return f"KVM  ESP32={e}  BLE={b}  FWD={f}"


class TrayIcon:
    """pystray-based status tray icon; same public interface as StatusWindow."""

    # Optional callbacks set by main() after construction
    on_toggle: Optional[Callable] = None
    on_quit:   Optional[Callable] = None

    def __init__(self) -> None:
        self._esp32:      bool          = False
        self._ble:        Optional[bool] = None
        self._forwarding: bool          = False
        self._icon:       Optional[pystray.Icon] = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public interface (matches StatusWindow)
    # ------------------------------------------------------------------

    def set_esp32(self, connected: bool) -> None:
        with self._lock:
            self._esp32 = connected
        self._refresh()

    def set_ble(self, connected: Optional[bool]) -> None:
        with self._lock:
            self._ble = connected
        self._refresh()

    def set_forwarding(self, enabled: bool) -> None:
        with self._lock:
            self._forwarding = enabled
        self._refresh()

    def after(self, ms: int, func: Callable) -> None:
        """Schedule func to run after ms milliseconds (thread-safe)."""
        t = threading.Timer(ms / 1000.0, func)
        t.daemon = True
        t.start()

    def run(self) -> None:
        """Start the tray icon event loop (blocks until close() is called)."""
        menu = pystray.Menu(
            pystray.MenuItem("Toggle Forwarding  (Ctrl+Alt+K)", self._on_toggle_click),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit  (Ctrl+Alt+X)", None, enabled=False),
        )
        self._icon = pystray.Icon(
            "ESP32 KVM",
            self._make_image(),
            self._make_title(),
            menu,
        )
        self._icon.run()

    def close(self) -> None:
        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _make_image(self) -> Image.Image:
        with self._lock:
            return _make_image(self._esp32, self._ble, self._forwarding)

    def _make_title(self) -> str:
        with self._lock:
            return _make_title(self._esp32, self._ble, self._forwarding)

    def _refresh(self) -> None:
        if self._icon:
            self._icon.icon  = self._make_image()
            self._icon.title = self._make_title()

    def _on_toggle_click(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if self.on_toggle:
            self.on_toggle()

    def _on_quit_click(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if self.on_quit:
            self.on_quit()

"""
macOS keyboard hook using pynput (backed by Quartz CGEventTap).

Accessibility permission is required:
  System Settings -> Privacy & Security -> Accessibility -> allow Terminal / Python
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from pynput import keyboard

from .base import KeyboardHookBase
from .hid_keycodes import char_to_hid, special_key_to_hid, macos_vk_to_hid, MODIFIER_KEY_MAP

log = logging.getLogger(__name__)


def _check_accessibility() -> None:
    """Log a warning if accessibility permission is likely missing."""
    try:
        from ApplicationServices import AXIsProcessTrusted  # type: ignore
        if not AXIsProcessTrusted():
            log.warning(
                "Accessibility permission is not granted.\n"
                "  Go to: System Settings -> Privacy & Security -> Accessibility\n"
                "  and enable your Terminal / Python executable."
            )
    except (ImportError, AttributeError):
        pass  # Not available; pynput will raise its own error if needed


class MacOSKeyboardHook(KeyboardHookBase):
    def __init__(self) -> None:
        self._listener: keyboard.Listener | None = None
        self._on_press: Callable | None = None
        self._on_release: Callable | None = None
        self._active_modifiers: int = 0
        self._lock = threading.Lock()

    def start(self, on_press: Callable, on_release: Callable) -> None:
        _check_accessibility()
        self._on_press = on_press
        self._on_release = on_release
        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
            suppress=False,
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, key) -> tuple[int, int]:
        """Return (modifier_delta, keycode) for a given pynput key."""
        if isinstance(key, keyboard.Key):
            return special_key_to_hid(key)
        if isinstance(key, keyboard.KeyCode):
            # Use physical VK code first (IME-independent: works for Korean, etc.)
            if key.vk is not None:
                hid = macos_vk_to_hid(key.vk)
                if hid:
                    return (0, hid)
            # Fallback to char-based mapping
            if key.char:
                return char_to_hid(key.char)
        return (0, 0)

    def _handle_press(self, key) -> None:
        mod_delta, keycode = self._resolve(key)
        with self._lock:
            self._active_modifiers |= mod_delta
            current_mod = self._active_modifiers
        if self._on_press and (keycode or mod_delta):
            self._on_press(current_mod, keycode)

    def _handle_release(self, key) -> None:
        mod_delta, keycode = self._resolve(key)
        with self._lock:
            self._active_modifiers &= ~mod_delta
            current_mod = self._active_modifiers
        if self._on_release and (keycode or mod_delta):
            self._on_release(current_mod, keycode)

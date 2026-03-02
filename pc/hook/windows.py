"""
Windows keyboard hook using pynput.
Captures all key events and forwards them as (modifier, keycode) pairs.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

log = logging.getLogger(__name__)

from pynput import keyboard

from .base import KeyboardHookBase
from .hid_keycodes import char_to_hid, special_key_to_hid, MODIFIER_KEY_MAP


class WindowsKeyboardHook(KeyboardHookBase):
    def __init__(self) -> None:
        self._listener: keyboard.Listener | None = None
        self._on_press: Callable | None = None
        self._on_release: Callable | None = None
        self._active_modifiers: int = 0
        self._lock = threading.Lock()
        self._suppress: bool = False

    def start(self, on_press: Callable, on_release: Callable) -> None:
        self._on_press = on_press
        self._on_release = on_release
        self._restart_listener()

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener.join(timeout=2.0)  # Increased from 1.0 for complete Windows hook cleanup
            self._listener = None

    def set_suppress(self, suppress: bool) -> None:
        if self._suppress == suppress:
            return
        self._suppress = suppress
        if self._listener:
            self._restart_listener()

    def _restart_listener(self) -> None:
        import time
        old_listener = None
        if self._listener:
            old_listener = self._listener
            old_listener.stop()
            # Cannot join from within the listener thread itself (e.g. called
            # from a key callback during set_suppress). Skip join in that case;
            # the thread is already unwinding after the callback returns.
            if threading.current_thread() is not old_listener:
                old_listener.join(timeout=2.0)
            self._listener = None  # Explicitly clear old reference

        # Windows keyboard hook unhooking is asynchronous. We need to wait for the
        # OS to fully release the hook before creating a new listener. Empirically,
        # this requires ~1 second. Rather than a fixed sleep, we wait for the old
        # listener thread to actually terminate.
        if old_listener and hasattr(old_listener, '_thread') and old_listener._thread:
            for _ in range(100):  # up to 5 seconds with 0.05s polls
                if not old_listener._thread.is_alive():
                    break
                time.sleep(0.05)
            else:
                # Fallback: still apply the known-good delay
                time.sleep(0.5)

        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
            suppress=self._suppress,
        )
        self._listener.start()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, key) -> tuple[int, int]:
        """Return (modifier_delta, keycode) for a given pynput key."""
        if isinstance(key, keyboard.Key):
            return special_key_to_hid(key)
        if isinstance(key, keyboard.KeyCode):
            if key.vk == 0x15:  # VK_HANGUL (한/영) -> Ctrl+Space
                return (0x01, 0x2C)
            if key.char:
                return char_to_hid(key.char)
            # Fallback: try vk-based mapping (Windows virtual key codes)
            vk = key.vk
            if vk is not None:
                hid = _vk_to_hid(vk)
                return (0, hid)
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


# ---------------------------------------------------------------------------
# Windows Virtual Key -> HID Usage ID (keyboard page 0x07)
# Covers common keys not representable as characters.
# ---------------------------------------------------------------------------
_VK_HID: dict[int, int] = {
    0x08: 0x2A,  # VK_BACK -> Backspace
    0x09: 0x2B,  # VK_TAB
    0x0D: 0x28,  # VK_RETURN
    0x1B: 0x29,  # VK_ESCAPE
    0x20: 0x2C,  # VK_SPACE
    0x21: 0x4B,  # VK_PRIOR (Page Up)
    0x22: 0x4E,  # VK_NEXT  (Page Down)
    0x23: 0x4D,  # VK_END
    0x24: 0x4A,  # VK_HOME
    0x25: 0x50,  # VK_LEFT
    0x26: 0x52,  # VK_UP
    0x27: 0x4F,  # VK_RIGHT
    0x28: 0x51,  # VK_DOWN
    0x2C: 0x46,  # VK_SNAPSHOT (Print Screen)
    0x2D: 0x49,  # VK_INSERT
    0x2E: 0x4C,  # VK_DELETE
    # F1-F12
    0x70: 0x3A, 0x71: 0x3B, 0x72: 0x3C, 0x73: 0x3D,
    0x74: 0x3E, 0x75: 0x3F, 0x76: 0x40, 0x77: 0x41,
    0x78: 0x42, 0x79: 0x43, 0x7A: 0x44, 0x7B: 0x45,
    # Numpad
    0x60: 0x62, 0x61: 0x59, 0x62: 0x5A, 0x63: 0x5B,
    0x64: 0x5C, 0x65: 0x5D, 0x66: 0x5E, 0x67: 0x5F,
    0x68: 0x60, 0x69: 0x61,
    0x6A: 0x55,  # VK_MULTIPLY
    0x6B: 0x57,  # VK_ADD
    0x6D: 0x56,  # VK_SUBTRACT
    0x6E: 0x63,  # VK_DECIMAL
    0x6F: 0x54,  # VK_DIVIDE
    0x90: 0x53,  # VK_NUMLOCK
    0x91: 0x47,  # VK_SCROLL
    0x14: 0x39,  # VK_CAPITAL (Caps Lock)
    0x15: 0x90,  # VK_HANGUL -> HID Lang1 (한/영)
    0x19: 0x91,  # VK_HANJA  -> HID Lang2 (한자)
}


def _vk_to_hid(vk: int) -> int:
    if vk in _VK_HID:
        return _VK_HID[vk]
    # VK for A-Z: 0x41-0x5A maps to HID 0x04-0x1D
    if 0x41 <= vk <= 0x5A:
        return vk - 0x41 + 0x04
    # VK for 0-9: 0x30-0x39 maps to HID 0x27, 0x1E-0x26
    if vk == 0x30:
        return 0x27
    if 0x31 <= vk <= 0x39:
        return vk - 0x31 + 0x1E
    return 0

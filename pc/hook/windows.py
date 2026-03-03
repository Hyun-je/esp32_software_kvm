"""
Windows keyboard hook using the `keyboard` library.
Captures all key events and forwards them as (modifier, keycode) pairs.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

import keyboard as kb

from .base import KeyboardHookBase
from .hid_keycodes import char_to_hid

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Modifier key name -> HID modifier bitmask
# ---------------------------------------------------------------------------
_MODIFIER_NAME_MAP: dict[str, int] = {
    'left ctrl':     0x01,
    'right ctrl':    0x10,
    'left shift':    0x02,
    'right shift':   0x20,
    'left alt':      0x04,
    'right alt':     0x40,
    'left windows':  0x08,
    'right windows': 0x80,
    # Unsided fallbacks (keyboard lib may report these for some keyboards)
    'ctrl':          0x01,
    'shift':         0x02,
    'alt':           0x04,
    'windows':       0x08,
}

# ---------------------------------------------------------------------------
# keyboard library key name -> HID Usage ID (keyboard page 0x07)
# ---------------------------------------------------------------------------
_NAME_TO_HID: dict[str, int] = {
    'enter':        0x28,
    'esc':          0x29,
    'backspace':    0x2A,
    'tab':          0x2B,
    'space':        0x2C,
    'caps lock':    0x39,
    'f1':  0x3A, 'f2':  0x3B, 'f3':  0x3C, 'f4':  0x3D,
    'f5':  0x3E, 'f6':  0x3F, 'f7':  0x40, 'f8':  0x41,
    'f9':  0x42, 'f10': 0x43, 'f11': 0x44, 'f12': 0x45,
    'print screen': 0x46,
    'scroll lock':  0x47,
    'pause':        0x48,
    'insert':       0x49,
    'home':         0x4A,
    'page up':      0x4B,
    'delete':       0x4C,
    'end':          0x4D,
    'page down':    0x4E,
    'right':        0x4F,
    'left':         0x50,
    'down':         0x51,
    'up':           0x52,
    'num lock':     0x53,
    # Numpad operators
    'decimal':      0x63,
    'divide':       0x54,
    'multiply':     0x55,
    'subtract':     0x56,
    'add':          0x57,
    # Numpad digits (reported as 'num N' when numlock is on)
    'num 0': 0x62,
    'num 1': 0x59, 'num 2': 0x5A, 'num 3': 0x5B,
    'num 4': 0x5C, 'num 5': 0x5D, 'num 6': 0x5E,
    'num 7': 0x5F, 'num 8': 0x60, 'num 9': 0x61,
    # Korean IME
    'hanja':        0x91,  # HID Lang2 (한자)
    # Application / menu key
    'menu':         0x65,
    'apps':         0x65,
}


class WindowsKeyboardHook(KeyboardHookBase):
    def __init__(self) -> None:
        self._on_press: Callable | None = None
        self._on_release: Callable | None = None
        self._active_modifiers: int = 0
        self._lock = threading.Lock()
        self._suppress: bool = False
        self._hook = None

    def start(self, on_press: Callable, on_release: Callable) -> None:
        self._on_press = on_press
        self._on_release = on_release
        self._install_hook()

    def stop(self) -> None:
        self._uninstall_hook()

    def shutdown(self) -> None:
        # Directly uninstall any active hook without going through set_suppress():
        #   - avoids the early-return guard (suppress already False → no-op)
        #   - avoids the unnecessary hook reinstall cycle (unhook → reinstall non-suppress → unhook again)
        # Uninstalling a suppressing hook via kb.unhook() releases OS-level
        # suppression immediately, so no separate "switch to non-suppress" step needed.
        self._suppress = False
        self._uninstall_hook()

    def set_suppress(self, suppress: bool) -> None:
        if self._suppress == suppress:
            return
        self._suppress = suppress
        if self._hook is not None:
            self._uninstall_hook()
            self._install_hook()

    def _install_hook(self) -> None:
        # keyboard.hook() returns the callback itself; store it for unhook.
        self._hook = kb.hook(self._handle_event, suppress=self._suppress)

    def _uninstall_hook(self) -> None:
        if self._hook is not None:
            kb.unhook(self._hook)
            self._hook = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, event: kb.KeyboardEvent) -> tuple[int, int]:
        """Return (modifier_delta, keycode) for a keyboard event."""
        vk = getattr(event, 'vk', None)
        name = (event.name or '').lower()

        # VK_HANGUL (한/영) -> Ctrl+Space for iOS IME compatibility
        # keyboard lib reports scan 242 as 'hangeul'; also accept 'hangul' and VK 0x15
        if vk == 0x15 or name in ('hangul', 'hangeul'):
            return (0x01, 0x2C)

        # Modifier keys
        mod = _MODIFIER_NAME_MAP.get(name, 0)
        if mod:
            return (mod, 0)

        # Named special keys
        hid = _NAME_TO_HID.get(name)
        if hid is not None:
            return (0, hid)

        # Single printable character (a-z, 0-9, punctuation)
        if len(name) == 1:
            result = char_to_hid(name)
            if result != (0, 0):
                return result

        # VK-based fallback for any remaining unmapped keys
        if vk is not None:
            hid = _vk_to_hid(vk)
            return (0, hid)

        return (0, 0)

    def _handle_event(self, event: kb.KeyboardEvent) -> None:
        mod_delta, keycode = self._resolve(event)

        if event.event_type == kb.KEY_DOWN:
            with self._lock:
                self._active_modifiers |= mod_delta
                current_mod = self._active_modifiers
            if self._on_press and (keycode or mod_delta):
                self._on_press(current_mod, keycode)
        elif event.event_type == kb.KEY_UP:
            with self._lock:
                self._active_modifiers &= ~mod_delta
                current_mod = self._active_modifiers
            if self._on_release and (keycode or mod_delta):
                self._on_release(current_mod, keycode)


# ---------------------------------------------------------------------------
# Windows Virtual Key -> HID Usage ID (keyboard page 0x07)
# Fallback for keys not resolved by name lookup above.
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
    0x19: 0x91,  # VK_HANJA -> HID Lang2 (한자)
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

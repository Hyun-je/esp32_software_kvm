"""
HID Usage ID mapping tables.

References:
  - USB HID Usage Tables 1.4, Section 10 (Keyboard/Keypad Page 0x07)
  - pynput Key enum values and vk codes
"""

from pynput.keyboard import Key

# Modifier bitmask constants (HID spec)
MOD_LEFT_CTRL = 0x01
MOD_LEFT_SHIFT = 0x02
MOD_LEFT_ALT = 0x04
MOD_LEFT_GUI = 0x08
MOD_RIGHT_CTRL = 0x10
MOD_RIGHT_SHIFT = 0x20
MOD_RIGHT_ALT = 0x40
MOD_RIGHT_GUI = 0x80

def _key(name: str) -> "Key | None":
    """Return Key.<name> if it exists on this platform, else None."""
    return getattr(Key, name, None)


# pynput special Key -> HID keycode
# Keys absent on macOS (print_screen, scroll_lock, etc.) are skipped safely.
_SPECIAL_KEY_ENTRIES: list[tuple[str, int]] = [
    ("enter", 0x28),
    ("esc", 0x29),
    ("backspace", 0x2A),
    ("tab", 0x2B),
    ("space", 0x2C),
    ("caps_lock", 0x39),
    ("f1", 0x3A),
    ("f2", 0x3B),
    ("f3", 0x3C),
    ("f4", 0x3D),
    ("f5", 0x3E),
    ("f6", 0x3F),
    ("f7", 0x40),
    ("f8", 0x41),
    ("f9", 0x42),
    ("f10", 0x43),
    ("f11", 0x44),
    ("f12", 0x45),
    ("print_screen", 0x46),
    ("scroll_lock", 0x47),
    ("pause", 0x48),
    ("insert", 0x49),
    ("home", 0x4A),
    ("page_up", 0x4B),
    ("delete", 0x4C),
    ("end", 0x4D),
    ("page_down", 0x4E),
    ("right", 0x4F),
    ("left", 0x50),
    ("down", 0x51),
    ("up", 0x52),
    ("num_lock", 0x53),
    ("menu", 0x65),
    # Modifier keys — reported via MOD byte, not keycode
    ("ctrl_l", 0x00),
    ("ctrl_r", 0x00),
    ("shift_l", 0x00),
    ("shift_r", 0x00),
    ("alt_l", 0x00),
    ("alt_r", 0x00),
    ("cmd", 0x00),
    ("cmd_r", 0x00),
    ("ctrl", 0x00),
    ("shift", 0x00),
    ("alt", 0x00),
]

SPECIAL_KEY_MAP: dict[Key, int] = {
    k: v for name, v in _SPECIAL_KEY_ENTRIES if (k := _key(name)) is not None
}

# pynput special Key -> modifier bitmask (for keys that only set MOD)
_MODIFIER_KEY_ENTRIES: list[tuple[str, int]] = [
    ("ctrl_l", MOD_LEFT_CTRL),
    ("ctrl", MOD_LEFT_CTRL),
    ("ctrl_r", MOD_RIGHT_CTRL),
    ("shift_l", MOD_LEFT_SHIFT),
    ("shift", MOD_LEFT_SHIFT),
    ("shift_r", MOD_RIGHT_SHIFT),
    ("alt_l", MOD_LEFT_ALT),
    ("alt", MOD_LEFT_ALT),
    ("alt_r", MOD_RIGHT_ALT),
    ("cmd", MOD_LEFT_GUI),
    ("cmd_r", MOD_RIGHT_GUI),
]

MODIFIER_KEY_MAP: dict[Key, int] = {
    k: v for name, v in _MODIFIER_KEY_ENTRIES if (k := _key(name)) is not None
}

# ASCII character -> HID keycode (unshifted)
# Covers a-z (0x04-0x1D), 0-9, and common punctuation
_CHAR_MAP: dict[str, int] = {
    'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07,
    'e': 0x08, 'f': 0x09, 'g': 0x0A, 'h': 0x0B,
    'i': 0x0C, 'j': 0x0D, 'k': 0x0E, 'l': 0x0F,
    'm': 0x10, 'n': 0x11, 'o': 0x12, 'p': 0x13,
    'q': 0x14, 'r': 0x15, 's': 0x16, 't': 0x17,
    'u': 0x18, 'v': 0x19, 'w': 0x1A, 'x': 0x1B,
    'y': 0x1C, 'z': 0x1D,
    '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21,
    '5': 0x22, '6': 0x23, '7': 0x24, '8': 0x25,
    '9': 0x26, '0': 0x27,
    ' ': 0x2C,
    '-': 0x2D, '=': 0x2E,
    '[': 0x2F, ']': 0x30,
    '\\': 0x31, '#': 0x32,
    ';': 0x33, "'": 0x34,
    '`': 0x35,
    ',': 0x36, '.': 0x37, '/': 0x38,
}

# Shifted characters -> (HID keycode, requires_shift)
_SHIFTED_CHAR_MAP: dict[str, tuple[int, bool]] = {
    'A': (0x04, True), 'B': (0x05, True), 'C': (0x06, True), 'D': (0x07, True),
    'E': (0x08, True), 'F': (0x09, True), 'G': (0x0A, True), 'H': (0x0B, True),
    'I': (0x0C, True), 'J': (0x0D, True), 'K': (0x0E, True), 'L': (0x0F, True),
    'M': (0x10, True), 'N': (0x11, True), 'O': (0x12, True), 'P': (0x13, True),
    'Q': (0x14, True), 'R': (0x15, True), 'S': (0x16, True), 'T': (0x17, True),
    'U': (0x18, True), 'V': (0x19, True), 'W': (0x1A, True), 'X': (0x1B, True),
    'Y': (0x1C, True), 'Z': (0x1D, True),
    '!': (0x1E, True), '@': (0x1F, True), '#': (0x20, True), '$': (0x21, True),
    '%': (0x22, True), '^': (0x23, True), '&': (0x24, True), '*': (0x25, True),
    '(': (0x26, True), ')': (0x27, True),
    '_': (0x2D, True), '+': (0x2E, True),
    '{': (0x2F, True), '}': (0x30, True),
    '|': (0x31, True), '~': (0x35, True),
    ':': (0x33, True), '"': (0x34, True),
    '<': (0x36, True), '>': (0x37, True), '?': (0x38, True),
}


def char_to_hid(char: str) -> tuple[int, int]:
    """
    Convert a character to (modifier, hid_keycode).
    Returns (0, 0) if the character cannot be mapped.
    """
    if char in _CHAR_MAP:
        return (0, _CHAR_MAP[char])
    if char in _SHIFTED_CHAR_MAP:
        keycode, _ = _SHIFTED_CHAR_MAP[char]
        return (MOD_LEFT_SHIFT, keycode)
    return (0, 0)


def special_key_to_hid(key: Key) -> tuple[int, int]:
    """
    Convert a pynput special Key to (modifier_bitmask, hid_keycode).
    Modifier-only keys return (mod, 0).
    """
    mod = MODIFIER_KEY_MAP.get(key, 0)
    keycode = SPECIAL_KEY_MAP.get(key, 0)
    return (mod, keycode)


# macOS Carbon virtual key code -> HID keycode
# Physical key position, IME-independent (works for Korean, Japanese, etc.)
# Reference: HIToolbox/Events.h kVK_* constants
_MACOS_VK_TO_HID: dict[int, int] = {
    0x00: 0x04,  # kVK_ANSI_A
    0x01: 0x16,  # kVK_ANSI_S
    0x02: 0x07,  # kVK_ANSI_D
    0x03: 0x09,  # kVK_ANSI_F
    0x04: 0x0B,  # kVK_ANSI_H
    0x05: 0x0A,  # kVK_ANSI_G
    0x06: 0x1D,  # kVK_ANSI_Z
    0x07: 0x1B,  # kVK_ANSI_X
    0x08: 0x06,  # kVK_ANSI_C
    0x09: 0x19,  # kVK_ANSI_V
    0x0B: 0x05,  # kVK_ANSI_B
    0x0C: 0x14,  # kVK_ANSI_Q
    0x0D: 0x1A,  # kVK_ANSI_W
    0x0E: 0x08,  # kVK_ANSI_E
    0x0F: 0x15,  # kVK_ANSI_R
    0x10: 0x1C,  # kVK_ANSI_Y
    0x11: 0x17,  # kVK_ANSI_T
    0x12: 0x1E,  # kVK_ANSI_1
    0x13: 0x1F,  # kVK_ANSI_2
    0x14: 0x20,  # kVK_ANSI_3
    0x15: 0x21,  # kVK_ANSI_4
    0x16: 0x23,  # kVK_ANSI_6
    0x17: 0x22,  # kVK_ANSI_5
    0x18: 0x2E,  # kVK_ANSI_Equal
    0x19: 0x26,  # kVK_ANSI_9
    0x1A: 0x24,  # kVK_ANSI_7
    0x1B: 0x2D,  # kVK_ANSI_Minus
    0x1C: 0x25,  # kVK_ANSI_8
    0x1D: 0x27,  # kVK_ANSI_0
    0x1E: 0x30,  # kVK_ANSI_RightBracket
    0x1F: 0x12,  # kVK_ANSI_O
    0x20: 0x18,  # kVK_ANSI_U
    0x21: 0x2F,  # kVK_ANSI_LeftBracket
    0x22: 0x0C,  # kVK_ANSI_I
    0x23: 0x13,  # kVK_ANSI_P
    0x25: 0x0F,  # kVK_ANSI_L
    0x26: 0x0D,  # kVK_ANSI_J
    0x27: 0x34,  # kVK_ANSI_Quote
    0x28: 0x0E,  # kVK_ANSI_K
    0x29: 0x33,  # kVK_ANSI_Semicolon
    0x2A: 0x31,  # kVK_ANSI_Backslash
    0x2B: 0x36,  # kVK_ANSI_Comma
    0x2C: 0x38,  # kVK_ANSI_Slash
    0x2D: 0x11,  # kVK_ANSI_N
    0x2E: 0x10,  # kVK_ANSI_M
    0x2F: 0x37,  # kVK_ANSI_Period
    0x32: 0x35,  # kVK_ANSI_Grave
    # Special keys
    0x24: 0x28,  # kVK_Return
    0x30: 0x2B,  # kVK_Tab
    0x31: 0x2C,  # kVK_Space
    0x33: 0x2A,  # kVK_Delete (Backspace)
    0x35: 0x29,  # kVK_Escape
    0x39: 0x39,  # kVK_CapsLock
    0x75: 0x4C,  # kVK_ForwardDelete
    0x73: 0x4A,  # kVK_Home
    0x77: 0x4D,  # kVK_End
    0x74: 0x4B,  # kVK_PageUp
    0x79: 0x4E,  # kVK_PageDown
    0x7B: 0x50,  # kVK_LeftArrow
    0x7C: 0x4F,  # kVK_RightArrow
    0x7D: 0x51,  # kVK_DownArrow
    0x7E: 0x52,  # kVK_UpArrow
    # Function keys
    0x7A: 0x3A,  # kVK_F1
    0x78: 0x3B,  # kVK_F2
    0x63: 0x3C,  # kVK_F3
    0x76: 0x3D,  # kVK_F4
    0x60: 0x3E,  # kVK_F5
    0x61: 0x3F,  # kVK_F6
    0x62: 0x40,  # kVK_F7
    0x64: 0x41,  # kVK_F8
    0x65: 0x42,  # kVK_F9
    0x6D: 0x43,  # kVK_F10
    0x67: 0x44,  # kVK_F11
    0x6F: 0x45,  # kVK_F12
}


def macos_vk_to_hid(vk: int) -> int:
    """
    Convert a macOS Carbon virtual key code to HID keycode.
    Returns 0 if not mapped.
    """
    return _MACOS_VK_TO_HID.get(vk, 0)

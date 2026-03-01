"""
Serial packet protocol for PC <-> ESP32 communication.

Packet format (6 bytes):
  [0xAA] [TYPE] [MOD] [KEYCODE] [CHECKSUM] [0x55]

TYPE:
  0x01 = KEY_DOWN
  0x02 = KEY_UP
  0x03 = CONSUMER_KEY

MOD (HID modifier bitmask):
  bit0: Left Ctrl
  bit1: Left Shift
  bit2: Left Alt
  bit3: Left GUI (Win/Cmd)
  bit4: Right Ctrl
  bit5: Right Shift
  bit6: Right Alt
  bit7: Right GUI

CHECKSUM = TYPE XOR MOD XOR KEYCODE
"""

START_BYTE = 0xAA
END_BYTE = 0x55

KEY_DOWN = 0x01
KEY_UP = 0x02
CONSUMER_KEY = 0x03

PACKET_LEN = 6


def compute_checksum(event_type: int, modifier: int, keycode: int) -> int:
    return event_type ^ modifier ^ keycode


def encode(event_type: int, modifier: int, keycode: int) -> bytes:
    """Encode a key event into a 6-byte packet."""
    checksum = compute_checksum(event_type, modifier, keycode)
    return bytes([START_BYTE, event_type, modifier, keycode, checksum, END_BYTE])


def decode(data: bytes) -> dict | None:
    """
    Decode a 6-byte packet received from the ESP32.
    Returns a dict with keys: event_type, modifier, keycode
    Returns None if the packet is invalid.
    """
    if len(data) != PACKET_LEN:
        return None
    if data[0] != START_BYTE or data[5] != END_BYTE:
        return None
    event_type, modifier, keycode, checksum = data[1], data[2], data[3], data[4]
    if compute_checksum(event_type, modifier, keycode) != checksum:
        return None
    return {"event_type": event_type, "modifier": modifier, "keycode": keycode}

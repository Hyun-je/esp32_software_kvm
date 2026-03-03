import sys

# Serial port (auto-detected by default, override with --port)
if sys.platform == "win32":
    SERIAL_PORT = "COM3"
else:
    SERIAL_PORT = "/dev/cu.usbmodem*"  # ESP32-C3 USB CDC on macOS

BAUD_RATE = 115200

# If True, key events are also passed through to the local OS
PASSTHROUGH = True

# ESP32-C3 USB VID/PID for auto-detection
ESP32_VID = 0x303A  # Espressif Systems
ESP32_PIDS = (0x1001, 0x0002)  # ESP32-C3 USB CDC PIDs

# Hotkey to toggle ESP32 forwarding on/off.
# Values are HID modifier bitmask and HID keycode.
# Default: Ctrl+Alt+K  (MOD_LEFT_CTRL=0x01 | MOD_LEFT_ALT=0x04 => 0x05, K=0x0E)
TOGGLE_MOD: int = 0x05   # Left Ctrl + Left Alt
TOGGLE_KEY: int = 0x0E   # K

# Hotkey to disable forwarding and quit after 0.5 s.
# Default: Ctrl+Alt+X  (same modifier mask, X=0x1B)
QUIT_MOD: int = 0x05   # Left Ctrl + Left Alt
QUIT_KEY: int = 0x1B   # X

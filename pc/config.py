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

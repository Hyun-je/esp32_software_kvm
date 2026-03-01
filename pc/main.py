#!/usr/bin/env python3
"""
ESP32 Software KVM - PC side entry point.

Hooks keyboard input and forwards key events to the ESP32 via USB Serial.
The ESP32 re-emits the keystrokes over BLE HID to a paired iPhone.

Usage:
    python main.py [--port PORT] [--baud BAUD] [--no-passthrough] [--list-ports]
"""

from __future__ import annotations

import argparse
import signal
import sys
import time

import serial.tools.list_ports

from protocol import packet as pkt
from serial_sender.sender import SerialSender
from hook.hid_keycodes import MOD_LEFT_CTRL
import config as cfg

# HID keycode for CapsLock; remapped to Ctrl+Space for iOS Korean/English toggle
_CAPS_LOCK_HID = 0x39
_SPACE_HID = 0x2C


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ESP32 Software KVM — keyboard forwarder"
    )
    parser.add_argument("--port", default=None, help="Serial port (e.g. COM3, /dev/cu.usbmodemXXX)")
    parser.add_argument("--baud", type=int, default=cfg.BAUD_RATE, help="Baud rate (default: 115200)")
    parser.add_argument("--no-passthrough", action="store_true", help="Suppress local key delivery")
    parser.add_argument("--list-ports", action="store_true", help="List available serial ports and exit")
    return parser


def _list_ports() -> None:
    ports = list(serial.tools.list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return
    print("Available serial ports:")
    for p in ports:
        vid_pid = f"VID:PID={p.vid:04X}:{p.pid:04X}" if p.vid else ""
        print(f"  {p.device:20s}  {p.description}  {vid_pid}")


def _get_hook():
    """Return the platform-appropriate keyboard hook instance."""
    if sys.platform == "win32":
        from hook.windows import WindowsKeyboardHook
        return WindowsKeyboardHook()
    elif sys.platform == "darwin":
        from hook.macos import MacOSKeyboardHook
        return MacOSKeyboardHook()
    else:
        print(f"Unsupported platform: {sys.platform}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    args = _build_arg_parser().parse_args()

    if args.list_ports:
        _list_ports()
        return

    # ------------------------------------------------------------------
    # Serial sender
    # ------------------------------------------------------------------
    sender = SerialSender(port=args.port, baud=args.baud)
    try:
        sender.connect()
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)

    passthrough = not args.no_passthrough

    # ------------------------------------------------------------------
    # Keyboard hook callbacks
    # ------------------------------------------------------------------
    def on_press(modifier: int, keycode: int) -> None:
        if keycode == 0 and modifier == 0:
            return
        # Remap CapsLock → Ctrl+Space so iPhone toggles Korean/English input
        if keycode == _CAPS_LOCK_HID and modifier == 0:
            print("[REMAP] CapsLock → Ctrl+Space (iOS language switch)")
            sender.send_key_event(pkt.KEY_DOWN, MOD_LEFT_CTRL, _SPACE_HID)
            sender.send_key_event(pkt.KEY_UP, MOD_LEFT_CTRL, _SPACE_HID)
            return
        print(f"[KEY_DOWN] mod=0x{modifier:02X} keycode=0x{keycode:02X}")
        sent = sender.send_key_event(pkt.KEY_DOWN, modifier, keycode)
        if not sent:
            print("[WARN] Packet dropped — not connected", file=sys.stderr)

    def on_release(modifier: int, keycode: int) -> None:
        if keycode == 0 and modifier == 0:
            return
        # CapsLock release is suppressed — already handled atomically on press
        if keycode == _CAPS_LOCK_HID and modifier == 0:
            return
        print(f"[KEY_UP]   mod=0x{modifier:02X} keycode=0x{keycode:02X}")
        sender.send_key_event(pkt.KEY_UP, modifier, keycode)

    hook = _get_hook()

    # ------------------------------------------------------------------
    # Graceful shutdown on Ctrl+C / SIGTERM
    # ------------------------------------------------------------------
    stop_event = [False]

    # Read and print ESP32 serial log output in background
    import threading

    def _esp32_log_reader():
        while not stop_event[0]:
            try:
                if sender._serial and sender._serial.is_open and sender._serial.in_waiting:
                    line = sender._serial.readline().decode("utf-8", errors="replace").rstrip()
                    if line:
                        print(f"[ESP32] {line}")
            except Exception:
                pass
            time.sleep(0.01)

    log_thread = threading.Thread(target=_esp32_log_reader, daemon=True, name="esp32-log")
    log_thread.start()

    def _shutdown(sig=None, frame=None) -> None:
        stop_event[0] = True
        hook.stop()
        sender.disconnect()
        print("\n[INFO] Stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # ------------------------------------------------------------------
    # Start hooking
    # ------------------------------------------------------------------
    print(f"[INFO] Keyboard hook active. passthrough={'ON' if passthrough else 'OFF'}")
    print("[INFO] Press Ctrl+C to stop.")

    hook.start(on_press, on_release)

    # Keep the main thread alive
    while not stop_event[0]:
        time.sleep(0.1)


if __name__ == "__main__":
    main()

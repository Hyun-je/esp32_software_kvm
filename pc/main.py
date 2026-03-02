#!/usr/bin/env python3
"""
ESP32 Software KVM - PC side entry point.

Hooks keyboard input and forwards key events to the ESP32 via USB Serial.
The ESP32 re-emits the keystrokes over BLE HID to a paired iPhone.

Usage:
    python main.py [--port PORT] [--baud BAUD] [--list-ports] [--verbose]
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import threading
import time

import serial.tools.list_ports

from protocol import packet as pkt
from serial_sender.sender import SerialSender
from hook.hid_keycodes import MOD_LEFT_CTRL
from gui.status_window import StatusWindow
import config as cfg

log = logging.getLogger("kvm")
esp32_log = logging.getLogger("esp32")

# HID keycode for CapsLock; remapped to Ctrl+Space for iOS Korean/English toggle
_CAPS_LOCK_HID = 0x39
_SPACE_HID = 0x2C


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ESP32 Software KVM — keyboard forwarder"
    )
    parser.add_argument("--port", default=None, help="Serial port (e.g. COM3, /dev/cu.usbmodemXXX)")
    parser.add_argument("--baud", type=int, default=cfg.BAUD_RATE, help="Baud rate (default: 115200)")
    parser.add_argument("--list-ports", action="store_true", help="List available serial ports and exit")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable DEBUG logging (key events)")
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

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

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
        log.error(exc)
        sys.exit(1)

    # ------------------------------------------------------------------
    # Status window
    # ------------------------------------------------------------------
    window = StatusWindow(on_close=lambda: _shutdown())
    window.set_esp32(True)    # just connected
    window.set_ble(None)      # unknown until ESP32 reports
    window.set_forwarding(True)

    # ------------------------------------------------------------------
    # Forwarding toggle state (Ctrl+Alt+K to switch on/off)
    # ------------------------------------------------------------------
    _forwarding = [True]  # list so inner functions can mutate it
    _pressed_keys: set[int] = set()  # keycodes sent as KEY_DOWN but not yet KEY_UP'd

    # ------------------------------------------------------------------
    # Keyboard hook callbacks
    # ------------------------------------------------------------------
    def on_press(modifier: int, keycode: int) -> None:
        if keycode == 0 and modifier == 0:
            return
        # Toggle forwarding when the hotkey is pressed
        if modifier == cfg.TOGGLE_MOD and keycode == cfg.TOGGLE_KEY:
            _forwarding[0] = not _forwarding[0]
            state = "ON" if _forwarding[0] else "OFF"
            log.info("Forwarding %s (Ctrl+Alt+K)", state)
            window.set_forwarding(_forwarding[0])
            hook.set_suppress(_forwarding[0])
            sender.send_forwarding_state(_forwarding[0])
            if _forwarding[0]:
                sender.send_status_request()
            return
        if not _forwarding[0]:
            return
        # Remap CapsLock → Ctrl+Space so iPhone toggles Korean/English input
        if keycode == _CAPS_LOCK_HID and modifier == 0:
            log.debug("CapsLock → Ctrl+Space (iOS language switch)")
            sender.send_key_event(pkt.KEY_DOWN, MOD_LEFT_CTRL, _SPACE_HID)
            sender.send_key_event(pkt.KEY_UP, MOD_LEFT_CTRL, _SPACE_HID)
            return
        log.debug("KEY_DOWN mod=0x%02X keycode=0x%02X", modifier, keycode)
        sent = sender.send_key_event(pkt.KEY_DOWN, modifier, keycode)
        if sent and keycode:
            _pressed_keys.add(keycode)
        if not sent:
            log.warning("Packet dropped — not connected")

    def on_release(modifier: int, keycode: int) -> None:
        if keycode == 0 and modifier == 0:
            return
        # Toggle hotkey release is always suppressed
        if modifier == cfg.TOGGLE_MOD and keycode == cfg.TOGGLE_KEY:
            return
        # If KEY_DOWN was sent for this key, always send KEY_UP regardless of
        # forwarding state — prevents stuck keys when toggling OFF while holding keys
        if keycode in _pressed_keys:
            _pressed_keys.discard(keycode)
            log.debug("KEY_UP   mod=0x%02X keycode=0x%02X", modifier, keycode)
            sender.send_key_event(pkt.KEY_UP, modifier, keycode)
            return
        if not _forwarding[0]:
            return
        # CapsLock release is suppressed — already handled atomically on press
        if keycode == _CAPS_LOCK_HID and modifier == 0:
            return
        log.debug("KEY_UP   mod=0x%02X keycode=0x%02X", modifier, keycode)
        sender.send_key_event(pkt.KEY_UP, modifier, keycode)

    hook = _get_hook()

    # ------------------------------------------------------------------
    # Graceful shutdown on Ctrl+C / SIGTERM / window close
    # ------------------------------------------------------------------
    stop_event = [False]

    def _shutdown(sig=None, frame=None) -> None:
        if stop_event[0]:
            return
        stop_event[0] = True
        hook.stop()
        # Release all keys that were sent as KEY_DOWN but not yet KEY_UP'd.
        # This prevents stuck keys on the iPhone when the program exits.
        for keycode in list(_pressed_keys):
            sender.send_key_event(pkt.KEY_UP, 0, keycode)
        _pressed_keys.clear()
        # Belt-and-suspenders: send a zero-keycode KEY_UP which triggers
        # releaseAll() on the ESP32 side regardless of its internal state.
        sender.send_key_event(pkt.KEY_UP, 0, 0)
        time.sleep(0.05)  # let the serial TX buffer drain before closing
        sender.disconnect()
        window.close()
        log.info("Stopped.")
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # ------------------------------------------------------------------
    # ESP32 serial log reader — also parses BLE connection status
    # ------------------------------------------------------------------
    def _esp32_log_reader():
        while not stop_event[0]:
            line = sender.read_line()
            if line:
                esp32_log.debug(line)
                if "[KVM] BLE connected." in line or "[KVM] BLE status: connected" in line:
                    window.set_ble(True)
                elif "[KVM] BLE disconnected." in line or "[KVM] BLE status: disconnected" in line:
                    window.set_ble(False)
            else:
                time.sleep(0.01)

    threading.Thread(target=_esp32_log_reader, daemon=True, name="esp32-log").start()

    # ------------------------------------------------------------------
    # Periodic ESP32 serial connection poll (updates the ESP32 LED)
    # ------------------------------------------------------------------
    def _poll_esp32():
        window.set_esp32(sender.is_connected)
        window.after(500, _poll_esp32)

    window.after(500, _poll_esp32)

    # Request BLE status and sync forwarding state once the GUI event loop starts
    window.after(200, sender.send_status_request)
    window.after(250, lambda: sender.send_forwarding_state(True))

    # ------------------------------------------------------------------
    # Start hooking
    # ------------------------------------------------------------------
    log.info("Keyboard hook active. forwarding=ON (PC input suppressed)")
    log.info("Press Ctrl+Alt+K to toggle forwarding. Ctrl+C to stop.")

    hook.start(on_press, on_release)
    hook.set_suppress(True)  # forwarding starts ON → suppress PC delivery

    # tkinter event loop — runs until the window is closed
    window.run()


if __name__ == "__main__":
    main()

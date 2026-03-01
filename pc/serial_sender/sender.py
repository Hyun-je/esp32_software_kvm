"""
Serial sender: manages the connection to ESP32 and sends key event packets.
Includes automatic reconnection logic on disconnect.
"""

from __future__ import annotations

import sys
import threading
import time
import glob
from typing import Optional

import serial
import serial.tools.list_ports

from protocol import packet as pkt
import config


class SerialSender:
    RECONNECT_INTERVAL = 2.0  # seconds between reconnect attempts

    def __init__(self, port: str | None = None, baud: int = config.BAUD_RATE) -> None:
        self._port = port  # None = auto-detect
        self._baud = baud
        self._serial: serial.Serial | None = None
        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """Open the serial port (auto-detect if port not specified)."""
        port = self._port or self._auto_detect_port()
        if port is None:
            raise RuntimeError("ESP32 serial port not found. Use --port to specify manually.")
        self._open(port)
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="serial-monitor"
        )
        self._monitor_thread.start()

    def disconnect(self) -> None:
        """Close the serial port and stop the monitor thread."""
        self._running = False
        with self._lock:
            if self._serial and self._serial.is_open:
                self._serial.close()
                self._serial = None

    def send_key_event(self, event_type: int, modifier: int, keycode: int) -> bool:
        """
        Encode and send a key event packet.
        Returns True on success, False if the port is not open.
        """
        data = pkt.encode(event_type, modifier, keycode)
        with self._lock:
            if self._serial is None or not self._serial.is_open:
                return False
            try:
                self._serial.write(data)
                return True
            except serial.SerialException as exc:
                print(f"[SerialSender] Write error: {exc}", file=sys.stderr)
                self._serial = None
                return False

    @property
    def is_connected(self) -> bool:
        with self._lock:
            return self._serial is not None and self._serial.is_open

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _open(self, port: str) -> None:
        with self._lock:
            try:
                self._serial = serial.Serial(port, self._baud, timeout=1)
                print(f"[SerialSender] Connected to {port} @ {self._baud} baud")
            except serial.SerialException as exc:
                self._serial = None
                raise RuntimeError(f"Cannot open serial port {port}: {exc}") from exc

    def _monitor_loop(self) -> None:
        """Background thread: detect disconnects and attempt reconnection."""
        while self._running:
            time.sleep(self.RECONNECT_INTERVAL)
            if not self._running:
                break
            with self._lock:
                connected = self._serial is not None and self._serial.is_open
            if not connected:
                print("[SerialSender] Connection lost. Attempting reconnect...", file=sys.stderr)
                port = self._port or self._auto_detect_port()
                if port:
                    try:
                        self._open(port)
                    except RuntimeError as exc:
                        print(f"[SerialSender] Reconnect failed: {exc}", file=sys.stderr)

    @staticmethod
    def _auto_detect_port() -> str | None:
        """Find the first serial port matching ESP32 VID/PID."""
        for info in serial.tools.list_ports.comports():
            if info.vid == config.ESP32_VID and info.pid in config.ESP32_PIDS:
                return info.device

        # Fallback: glob for common ESP32-C3 CDC port names on macOS
        if sys.platform == "darwin":
            matches = glob.glob("/dev/cu.usbmodem*")
            if matches:
                return matches[0]

        return None

"""Serial connection and Qt integration for the DPS-150.

A background QThread reads the serial stream, de-frames and decodes it, and
emits value dicts (see protocol.parse_payload). All commands are written from
the calling (GUI) thread; pyserial supports one concurrent reader + writer.
"""

from __future__ import annotations

import time

import serial
from PySide6.QtCore import QObject, QThread, Signal
from serial.tools import list_ports

from . import protocol

# The device drops commands sent back-to-back; the reference implementation
# waits 50 ms after each write.
_WRITE_GAP_S = 0.05


def available_ports() -> list[tuple[str, str]]:
    """Return (device, description) for likely serial ports, USB ones first."""
    ports = sorted(
        list_ports.comports(),
        key=lambda p: (p.vid is None, p.device),
    )
    return [(p.device, p.description) for p in ports]


class _ReaderThread(QThread):
    values = Signal(dict)
    failed = Signal(str)

    def __init__(self, ser: serial.Serial, parent: QObject | None = None):
        super().__init__(parent)
        self._ser = ser

    def run(self) -> None:
        parser = protocol.FrameParser()
        while not self.isInterruptionRequested():
            try:
                chunk = self._ser.read(1024)
            except (serial.SerialException, OSError) as e:
                self.failed.emit(str(e))
                return
            if not chunk:
                continue
            for frame in parser.feed(chunk):
                values = protocol.parse_payload(frame.register, frame.data)
                if values:
                    self.values.emit(values)


class DPS150(QObject):
    """Connection to one DPS-150. Safe to reuse across connect/disconnect."""

    valuesChanged = Signal(dict)
    connectionChanged = Signal(bool, str)  # (connected, port or error message)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._ser: serial.Serial | None = None
        self._reader: _ReaderThread | None = None

    @property
    def is_connected(self) -> bool:
        return self._ser is not None

    def connect_to(self, port: str) -> None:
        if self._ser is not None:
            return
        try:
            ser = serial.Serial(
                port, baudrate=115200, timeout=0.05, write_timeout=1.0
            )
        except (serial.SerialException, OSError) as e:
            self.connectionChanged.emit(False, str(e))
            return
        self._ser = ser
        self._reader = _ReaderThread(ser, self)
        self._reader.values.connect(self.valuesChanged)
        self._reader.failed.connect(self._on_reader_failed)
        self._reader.start()
        try:
            self._send(protocol.encode_session(True))
            self._send(protocol.encode_baud(115200))
            for reg in (
                protocol.MODEL_NAME,
                protocol.HARDWARE_VERSION,
                protocol.FIRMWARE_VERSION,
            ):
                self._send(protocol.encode_get(reg))
            self._send(protocol.encode_set_byte(protocol.METERING_ENABLE, 1))
            self._send(protocol.encode_get(protocol.ALL))
        except (serial.SerialException, OSError) as e:
            self._teardown()
            self.connectionChanged.emit(False, str(e))
            return
        self.connectionChanged.emit(True, port)

    def disconnect_from(self) -> None:
        if self._ser is None:
            return
        try:
            self._send(protocol.encode_session(False))
        except (serial.SerialException, OSError):
            pass
        self._teardown()
        self.connectionChanged.emit(False, "")

    def _teardown(self) -> None:
        if self._reader is not None:
            self._reader.requestInterruption()
            self._reader.wait(1000)
            self._reader = None
        if self._ser is not None:
            try:
                self._ser.close()
            except (serial.SerialException, OSError):
                pass
            self._ser = None

    def _on_reader_failed(self, message: str) -> None:
        if self._ser is None:
            return
        self._teardown()
        self.connectionChanged.emit(False, f"Connection lost: {message}")

    def _send(self, frame: bytes) -> None:
        if self._ser is None:
            return
        self._ser.write(frame)
        time.sleep(_WRITE_GAP_S)

    # Commands

    def set_voltage(self, volts: float) -> None:
        self.set_float(protocol.VOLTAGE_SET, volts)

    def set_current(self, amps: float) -> None:
        self.set_float(protocol.CURRENT_SET, amps)

    def set_output(self, on: bool) -> None:
        self.set_byte(protocol.OUTPUT_ENABLE, 1 if on else 0)

    def set_float(self, register: int, value: float) -> None:
        self._send_checked(protocol.encode_set_float(register, value))

    def set_byte(self, register: int, value: int) -> None:
        self._send_checked(protocol.encode_set_byte(register, value))

    def refresh(self) -> None:
        self._send_checked(protocol.encode_get(protocol.ALL))

    def _send_checked(self, frame: bytes) -> None:
        try:
            self._send(frame)
        except (serial.SerialException, OSError) as e:
            self._teardown()
            self.connectionChanged.emit(False, f"Connection lost: {e}")

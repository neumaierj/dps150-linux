"""Binary serial protocol for the FNIRSI DPS-150 power supply.

Pure functions and stateful-but-I/O-free parsing only, so everything here is
unit-testable without hardware.

Frame layout (both directions):

    [header] [command] [register] [len] [data ...] [checksum]

- header: 0xF1 host->device, 0xF0 device->host
- checksum: (register + len + sum(data)) % 256
- floats are IEEE-754 32-bit little-endian

Protocol reverse-engineered by cho45 (https://github.com/cho45/fnirsi-dps-150).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

HEADER_INPUT = 0xF0  # device -> host
HEADER_OUTPUT = 0xF1  # host -> device

CMD_GET = 0xA1
CMD_BAUD = 0xB0
CMD_SET = 0xB1
CMD_SESSION = 0xC1

# Registers (float payload unless noted)
INPUT_VOLTAGE = 192
VOLTAGE_SET = 193
CURRENT_SET = 194
OUTPUT_VIP = 195  # 3 floats: output voltage, current, power
TEMPERATURE = 196
# Groups 1-6: voltage/current setpoint pairs at 197/198 .. 207/208
OVP = 209
OCP = 210
OPP = 211
OTP = 212
LVP = 213
BRIGHTNESS = 214  # byte
VOLUME = 215  # byte
METERING_ENABLE = 216  # byte
OUTPUT_CAPACITY = 217  # Ah
OUTPUT_ENERGY = 218  # Wh
OUTPUT_ENABLE = 219  # byte
PROTECTION_STATE = 220  # byte, index into PROTECTION_STATES
MODE = 221  # byte, 0=CC 1=CV
MODEL_NAME = 222  # string
HARDWARE_VERSION = 223  # string
FIRMWARE_VERSION = 224  # string
UPPER_LIMIT_VOLTAGE = 226
UPPER_LIMIT_CURRENT = 227
ALL = 255  # full parameter dump

PROTECTION_STATES = ("", "OVP", "OCP", "OPP", "OTP", "LVP", "REP")

BAUD_RATES = (9600, 19200, 38400, 57600, 115200)


def group_voltage_set(group: int) -> int:
    """Register for group 1-6 voltage setpoint."""
    if not 1 <= group <= 6:
        raise ValueError(f"group must be 1-6, got {group}")
    return 197 + 2 * (group - 1)


def group_current_set(group: int) -> int:
    """Register for group 1-6 current setpoint."""
    if not 1 <= group <= 6:
        raise ValueError(f"group must be 1-6, got {group}")
    return 198 + 2 * (group - 1)


def checksum(register: int, data: bytes) -> int:
    return (register + len(data) + sum(data)) % 256


@dataclass(frozen=True)
class Frame:
    register: int
    data: bytes


def encode(command: int, register: int, data: bytes) -> bytes:
    return bytes(
        [HEADER_OUTPUT, command, register, len(data), *data, checksum(register, data)]
    )


def encode_get(register: int) -> bytes:
    return encode(CMD_GET, register, b"\x00")


def encode_set_float(register: int, value: float) -> bytes:
    return encode(CMD_SET, register, struct.pack("<f", value))


def encode_set_byte(register: int, value: int) -> bytes:
    return encode(CMD_SET, register, bytes([value]))


def encode_session(start: bool) -> bytes:
    return encode(CMD_SESSION, 0, b"\x01" if start else b"\x00")


def encode_baud(rate: int = 115200) -> bytes:
    return encode(CMD_BAUD, 0, bytes([BAUD_RATES.index(rate) + 1]))


_SYNC = bytes([HEADER_INPUT, CMD_GET])


class FrameParser:
    """Incremental de-framer for the device->host byte stream.

    Feed it raw chunks as they arrive; it returns complete, checksum-valid
    frames and silently discards garbage and corrupt frames.
    """

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, chunk: bytes) -> list[Frame]:
        buf = self._buf
        buf.extend(chunk)
        frames: list[Frame] = []
        pos = 0
        while True:
            start = buf.find(_SYNC, pos)
            if start < 0:
                # Keep a trailing 0xF0 that may be the start of the next sync.
                if buf and buf[-1] == HEADER_INPUT:
                    del buf[: len(buf) - 1]
                else:
                    buf.clear()
                break
            if len(buf) - start < 5:
                del buf[:start]
                break
            length = buf[start + 3]
            end = start + 5 + length
            if len(buf) < end:
                del buf[:start]
                break
            register = buf[start + 2]
            data = bytes(buf[start + 4 : start + 4 + length])
            if buf[end - 1] == checksum(register, data):
                frames.append(Frame(register, data))
                pos = end
            else:
                pos = start + 1  # false sync or corrupt frame, resync
        return frames


def _f32(data: bytes, offset: int) -> float:
    return struct.unpack_from("<f", data, offset)[0]


def parse_payload(register: int, data: bytes) -> dict:
    """Decode a frame payload into named values.

    Returns a (possibly empty) dict of state updates, e.g.
    {"output_voltage": 5.0, "output_current": 0.1, "output_power": 0.5}.
    """
    if register == INPUT_VOLTAGE:
        return {"input_voltage": _f32(data, 0)}
    if register == VOLTAGE_SET:
        return {"set_voltage": _f32(data, 0)}
    if register == CURRENT_SET:
        return {"set_current": _f32(data, 0)}
    if register == OUTPUT_VIP:
        return {
            "output_voltage": _f32(data, 0),
            "output_current": _f32(data, 4),
            "output_power": _f32(data, 8),
        }
    if register == TEMPERATURE:
        return {"temperature": _f32(data, 0)}
    if register == OUTPUT_CAPACITY:
        return {"output_capacity": _f32(data, 0)}
    if register == OUTPUT_ENERGY:
        return {"output_energy": _f32(data, 0)}
    if register == OUTPUT_ENABLE:
        return {"output_on": data[0] == 1}
    if register == PROTECTION_STATE:
        return {"protection_state": PROTECTION_STATES[data[0]]}
    if register == MODE:
        return {"mode": "CC" if data[0] == 0 else "CV"}
    if register == MODEL_NAME:
        return {"model_name": data.decode("ascii", "replace")}
    if register == HARDWARE_VERSION:
        return {"hardware_version": data.decode("ascii", "replace")}
    if register == FIRMWARE_VERSION:
        return {"firmware_version": data.decode("ascii", "replace")}
    if register == UPPER_LIMIT_VOLTAGE:
        return {"upper_limit_voltage": _f32(data, 0)}
    if register == UPPER_LIMIT_CURRENT:
        return {"upper_limit_current": _f32(data, 0)}
    if register == ALL:
        return _parse_all(data)
    return {}


def _parse_all(data: bytes) -> dict:
    if len(data) < 111:
        return {}
    values = {
        "input_voltage": _f32(data, 0),
        "set_voltage": _f32(data, 4),
        "set_current": _f32(data, 8),
        "output_voltage": _f32(data, 12),
        "output_current": _f32(data, 16),
        "output_power": _f32(data, 20),
        "temperature": _f32(data, 24),
        # groups[0] is group 1: (voltage setpoint, current setpoint)
        "groups": [
            (_f32(data, 28 + 8 * g), _f32(data, 32 + 8 * g)) for g in range(6)
        ],
        "ovp": _f32(data, 76),
        "ocp": _f32(data, 80),
        "opp": _f32(data, 84),
        "otp": _f32(data, 88),
        "lvp": _f32(data, 92),
        "brightness": data[96],
        "volume": data[97],
        "metering_on": data[98] == 1,
        "output_capacity": _f32(data, 99),
        "output_energy": _f32(data, 103),
        "output_on": data[107] == 1,
        "protection_state": PROTECTION_STATES[data[108]],
        "mode": "CC" if data[109] == 0 else "CV",
    }
    if len(data) >= 119:
        values["upper_limit_voltage"] = _f32(data, 111)
        values["upper_limit_current"] = _f32(data, 115)
    return values

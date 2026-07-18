import struct

import pytest

from dps150 import protocol as p


def device_frame(register: int, data: bytes) -> bytes:
    """Build a checksum-valid device->host frame."""
    return bytes(
        [p.HEADER_INPUT, p.CMD_GET, register, len(data), *data, p.checksum(register, data)]
    )


def test_checksum():
    assert p.checksum(193, b"\x00\x00\xa0\x40") == (193 + 4 + 0xA0 + 0x40) % 256


def test_encode_set_float():
    frame = p.encode_set_float(p.VOLTAGE_SET, 5.0)
    assert frame == bytes([0xF1, 0xB1, 193, 4, 0x00, 0x00, 0xA0, 0x40, 165])


def test_encode_set_byte():
    frame = p.encode_set_byte(p.OUTPUT_ENABLE, 1)
    assert frame == bytes([0xF1, 0xB1, 219, 1, 1, (219 + 1 + 1) % 256])


def test_encode_get():
    frame = p.encode_get(p.MODEL_NAME)
    assert frame == bytes([0xF1, 0xA1, 222, 1, 0, (222 + 1) % 256])


def test_encode_session():
    assert p.encode_session(True) == bytes([0xF1, 0xC1, 0, 1, 1, 2])
    assert p.encode_session(False) == bytes([0xF1, 0xC1, 0, 1, 0, 1])


def test_encode_baud_115200():
    assert p.encode_baud(115200) == bytes([0xF1, 0xB0, 0, 1, 5, 6])


def test_group_registers():
    assert p.group_voltage_set(1) == 197
    assert p.group_current_set(1) == 198
    assert p.group_voltage_set(6) == 207
    assert p.group_current_set(6) == 208
    with pytest.raises(ValueError):
        p.group_voltage_set(0)
    with pytest.raises(ValueError):
        p.group_current_set(7)


def test_parser_single_frame():
    parser = p.FrameParser()
    payload = struct.pack("<fff", 5.0, 0.5, 2.5)
    frames = parser.feed(device_frame(p.OUTPUT_VIP, payload))
    assert len(frames) == 1
    assert frames[0].register == p.OUTPUT_VIP
    values = p.parse_payload(frames[0].register, frames[0].data)
    assert values == {
        "output_voltage": 5.0,
        "output_current": 0.5,
        "output_power": 2.5,
    }


def test_parser_split_across_chunks():
    parser = p.FrameParser()
    frame = device_frame(p.TEMPERATURE, struct.pack("<f", 31.5))
    assert parser.feed(frame[:3]) == []
    assert parser.feed(frame[3:5]) == []
    frames = parser.feed(frame[5:])
    assert len(frames) == 1
    assert p.parse_payload(frames[0].register, frames[0].data) == {"temperature": 31.5}


def test_parser_skips_garbage_and_multiple_frames():
    parser = p.FrameParser()
    f1 = device_frame(p.INPUT_VOLTAGE, struct.pack("<f", 20.0))
    f2 = device_frame(p.MODE, b"\x01")
    stream = b"\x12\x34\xf0" + f1 + b"\xff\xff" + f2
    frames = parser.feed(stream)
    assert [f.register for f in frames] == [p.INPUT_VOLTAGE, p.MODE]
    assert p.parse_payload(frames[1].register, frames[1].data) == {"mode": "CV"}


def test_parser_drops_corrupt_checksum():
    parser = p.FrameParser()
    good = device_frame(p.TEMPERATURE, struct.pack("<f", 25.0))
    bad = bytearray(device_frame(p.INPUT_VOLTAGE, struct.pack("<f", 20.0)))
    bad[-1] ^= 0xFF
    frames = parser.feed(bytes(bad) + good)
    assert [f.register for f in frames] == [p.TEMPERATURE]


def test_parse_byte_registers():
    assert p.parse_payload(p.OUTPUT_ENABLE, b"\x01") == {"output_on": True}
    assert p.parse_payload(p.OUTPUT_ENABLE, b"\x00") == {"output_on": False}
    assert p.parse_payload(p.PROTECTION_STATE, b"\x02") == {"protection_state": "OCP"}
    assert p.parse_payload(p.MODE, b"\x00") == {"mode": "CC"}
    assert p.parse_payload(p.MODEL_NAME, b"DPS-150") == {"model_name": "DPS-150"}


def make_all_dump() -> bytes:
    data = bytearray(139)
    struct.pack_into("<7f", data, 0, 20.0, 5.0, 1.0, 4.99, 0.25, 1.25, 30.0)
    for g in range(6):
        struct.pack_into("<2f", data, 28 + 8 * g, 1.0 + g, 0.1 + g)
    struct.pack_into("<5f", data, 76, 31.0, 5.1, 155.0, 80.0, 2.0)
    data[96] = 8  # brightness
    data[97] = 3  # volume
    data[98] = 1  # metering on
    struct.pack_into("<2f", data, 99, 1.5, 7.5)  # Ah, Wh
    data[107] = 1  # output on
    data[108] = 0  # no protection tripped
    data[109] = 1  # CV
    struct.pack_into("<2f", data, 111, 30.5, 5.05)  # upper limits
    return bytes(data)


def test_parse_all_dump():
    values = p.parse_payload(p.ALL, make_all_dump())
    assert values["input_voltage"] == 20.0
    assert values["set_voltage"] == 5.0
    assert values["set_current"] == 1.0
    assert round(values["output_voltage"], 2) == 4.99
    assert values["temperature"] == 30.0
    assert len(values["groups"]) == 6
    assert values["groups"][0] == (1.0, pytest.approx(0.1))
    assert values["groups"][5] == (6.0, pytest.approx(5.1))
    assert values["ovp"] == 31.0
    assert values["lvp"] == 2.0
    assert values["brightness"] == 8
    assert values["volume"] == 3
    assert values["metering_on"] is True
    assert values["output_capacity"] == 1.5
    assert values["output_energy"] == 7.5
    assert values["output_on"] is True
    assert values["protection_state"] == ""
    assert values["mode"] == "CV"
    assert values["upper_limit_voltage"] == 30.5
    assert round(values["upper_limit_current"], 2) == 5.05


def test_parse_all_dump_via_parser_roundtrip():
    parser = p.FrameParser()
    frames = parser.feed(device_frame(p.ALL, make_all_dump()))
    assert len(frames) == 1
    assert frames[0].register == p.ALL


def test_parse_all_too_short_returns_empty():
    assert p.parse_payload(p.ALL, b"\x00" * 50) == {}

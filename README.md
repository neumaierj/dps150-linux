# DPS-150 for Linux

A Linux desktop application for the **FNIRSI DPS-150** portable programmable DC
power supply (0–30 V / 0–5 A, USB-PD powered) — a replacement for the
Windows-only vendor application.

Features:

- Live metering: output voltage / current / power, input voltage, temperature
- Voltage and current setpoints, output on/off, CC/CV indicator
- Protection status banner and editable OVP / OCP / OPP / OTP / LVP thresholds
- Six preset groups (M1–M6) with one-click apply
- Rolling live graph of V / I / P with pause and clear
- Accumulated capacity (Ah) / energy (Wh), display brightness, speaker volume

## Installation

Requires Python ≥ 3.10.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Running

Connect the DPS-150's **communication** USB-C port (the one next to the power
input) to your PC, then:

```sh
.venv/bin/dps150          # or: .venv/bin/python -m dps150
```

Pick the serial port (usually `/dev/ttyUSB0` or `/dev/ttyACM0`) and press
*Connect*.

### Serial port permissions

If opening the port fails with *Permission denied*, add yourself to the group
that owns the device (`dialout` on Fedora/Debian) and log out and back in:

```sh
sudo usermod -aG dialout $USER
```

## Development

```sh
.venv/bin/pip install -e .[dev]
.venv/bin/pytest
```

The protocol implementation lives in `dps150/protocol.py` (pure, unit-tested),
serial/Qt integration in `dps150/device.py`, and the UI panels under
`dps150/ui/`.

## Credits

The DPS-150 serial protocol was reverse-engineered by
[cho45/fnirsi-dps-150](https://github.com/cho45/fnirsi-dps-150); register
semantics were cross-checked against
[svenk123/dps150tool](https://github.com/svenk123/dps150tool).

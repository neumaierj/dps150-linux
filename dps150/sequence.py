"""Timed setpoint sequences (ramps, step profiles) — logic only, no widgets.

A sequence is a list of Step(time_s, voltage, current); current=None means
"leave the current limit unchanged". Times are relative to sequence start and
must be non-negative and strictly increasing.
"""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass

from PySide6.QtCore import QObject, QTimer, Signal

MAX_VOLTAGE = 30.0
MAX_CURRENT = 5.0


@dataclass(frozen=True)
class Step:
    time_s: float
    voltage: float
    current: float | None = None


def validate(
    steps: list[Step],
    max_voltage: float = MAX_VOLTAGE,
    max_current: float = MAX_CURRENT,
) -> None:
    """Raise ValueError if the sequence is not runnable."""
    if not steps:
        raise ValueError("sequence is empty")
    previous = -1.0
    for n, step in enumerate(steps, start=1):
        if step.time_s < 0:
            raise ValueError(f"step {n}: negative time")
        if step.time_s <= previous:
            raise ValueError(f"step {n}: times must be strictly increasing")
        previous = step.time_s
        if not 0.0 <= step.voltage <= max_voltage:
            raise ValueError(f"step {n}: voltage {step.voltage} outside 0-{max_voltage} V")
        if step.current is not None and not 0.0 <= step.current <= max_current:
            raise ValueError(f"step {n}: current {step.current} outside 0-{max_current} A")


def ramp_steps(
    start_v: float,
    end_v: float,
    duration_s: float,
    interval_s: float,
    max_voltage: float = MAX_VOLTAGE,
) -> list[Step]:
    """Evenly spaced voltage ramp including both endpoints, starting at t=0."""
    if duration_s <= 0:
        raise ValueError("duration must be positive")
    if interval_s <= 0:
        raise ValueError("interval must be positive")
    count = max(1, round(duration_s / interval_s))
    steps = [
        Step(
            time_s=round(k * duration_s / count, 6),
            voltage=round(start_v + (end_v - start_v) * k / count, 6),
        )
        for k in range(count + 1)
    ]
    validate(steps, max_voltage=max_voltage)
    return steps


def save_csv(path: str, steps: list[Step]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time_s", "voltage_V", "current_A"])
        for step in steps:
            writer.writerow(
                [step.time_s, step.voltage, "" if step.current is None else step.current]
            )


def load_csv(path: str, max_voltage: float = MAX_VOLTAGE) -> list[Step]:
    steps = []
    with open(path, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            raise ValueError("file is empty")
        for row in reader:
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) < 2:
                raise ValueError(f"row {reader.line_num}: need at least time and voltage")
            current_cell = row[2].strip() if len(row) > 2 else ""
            steps.append(
                Step(
                    time_s=float(row[0]),
                    voltage=float(row[1]),
                    current=float(current_cell) if current_cell else None,
                )
            )
    validate(steps, max_voltage=max_voltage)
    return steps


class SequenceRunner(QObject):
    """Plays a sequence against a monotonic clock with a single-shot timer chain.

    Emits setVoltage/setCurrent for each step; the caller wires these to the
    device, keeping the runner hardware-free.
    """

    setVoltage = Signal(float)
    setCurrent = Signal(float)
    stepStarted = Signal(int)  # index into the running sequence
    finished = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._steps: list[Step] = []
        self._index = 0
        self._t0 = 0.0
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)

    @property
    def is_running(self) -> bool:
        return self._timer.isActive() or self._index < len(self._steps)

    def start(self, steps: list[Step], max_voltage: float = MAX_VOLTAGE) -> None:
        validate(steps, max_voltage=max_voltage)
        self.stop()
        self._steps = list(steps)
        self._index = 0
        self._t0 = time.monotonic()
        self._schedule()

    def stop(self) -> None:
        self._timer.stop()
        self._steps = []
        self._index = 0

    def _schedule(self) -> None:
        # Delay from t0, not from now, so per-step jitter doesn't accumulate.
        due = self._t0 + self._steps[self._index].time_s
        self._timer.start(max(0, int((due - time.monotonic()) * 1000)))

    def _fire(self) -> None:
        if self._index >= len(self._steps):
            return
        step = self._steps[self._index]
        self.stepStarted.emit(self._index)
        self.setVoltage.emit(step.voltage)
        if step.current is not None:
            self.setCurrent.emit(step.current)
        self._index += 1
        if self._index < len(self._steps):
            self._schedule()
        else:
            self._steps = []
            self._index = 0
            self.finished.emit()

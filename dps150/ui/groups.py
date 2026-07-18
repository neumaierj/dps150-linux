"""Editor for the six preset groups (M1-M6)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGridLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from .. import protocol


class GroupsPanel(QWidget):
    setpointChanged = Signal(int, float)  # (register, value)
    applyRequested = Signal(float, float)  # (volts, amps)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        grid = QGridLayout(self)
        grid.addWidget(QLabel("Voltage"), 0, 1)
        grid.addWidget(QLabel("Current"), 0, 2)
        self._rows: list[tuple[QDoubleSpinBox, QDoubleSpinBox]] = []
        for group in range(1, 7):
            voltage = QDoubleSpinBox()
            voltage.setRange(0.0, 30.0)
            voltage.setDecimals(3)
            voltage.setSingleStep(0.1)
            voltage.setSuffix(" V")
            voltage.editingFinished.connect(
                lambda reg=protocol.group_voltage_set(group), s=voltage: (
                    self.setpointChanged.emit(reg, s.value())
                )
            )

            current = QDoubleSpinBox()
            current.setRange(0.0, 5.0)
            current.setDecimals(3)
            current.setSingleStep(0.1)
            current.setSuffix(" A")
            current.editingFinished.connect(
                lambda reg=protocol.group_current_set(group), s=current: (
                    self.setpointChanged.emit(reg, s.value())
                )
            )

            apply_button = QPushButton("Apply")
            apply_button.clicked.connect(
                lambda _=False, v=voltage, c=current: (
                    self.applyRequested.emit(v.value(), c.value())
                )
            )

            row = group  # header occupies row 0
            grid.addWidget(QLabel(f"M{group}"), row, 0)
            grid.addWidget(voltage, row, 1)
            grid.addWidget(current, row, 2)
            grid.addWidget(apply_button, row, 3)
            self._rows.append((voltage, current))
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

    def update_values(self, values: dict) -> None:
        if "groups" not in values:
            return
        for (voltage, current), (v, c) in zip(self._rows, values["groups"]):
            if not voltage.hasFocus():
                voltage.setValue(v)
            if not current.hasFocus():
                current.setValue(c)

"""Setpoint controls and output switch."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QValidator
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
)

from . import theme


class ClampSpinBox(QDoubleSpinBox):
    """Accepts typed values beyond the range and clamps them to min/max.

    A stock QDoubleSpinBox rejects keystrokes that would exceed the maximum,
    so e.g. "50" cannot even be typed; here it is accepted and becomes max.
    """

    def _to_number(self, text: str) -> float | None:
        stripped = text.removesuffix(self.suffix()).strip().replace(",", ".")
        try:
            return float(stripped)
        except ValueError:
            return None

    def validate(self, text: str, pos: int):
        stripped = text.removesuffix(self.suffix()).strip()
        if stripped in ("", "-", "+", ".", ",") or self._to_number(text) is not None:
            return QValidator.State.Acceptable, text, pos
        return QValidator.State.Invalid, text, pos

    def valueFromText(self, text: str) -> float:
        number = self._to_number(text)
        if number is None:
            return self.value()
        return min(max(number, self.minimum()), self.maximum())


class ControlsPanel(QWidget):
    voltageRequested = Signal(float)
    currentRequested = Signal(float)
    outputRequested = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._voltage = ClampSpinBox()
        self._voltage.setRange(0.0, 30.0)
        self._voltage.setDecimals(3)
        self._voltage.setSingleStep(0.1)
        self._voltage.setSuffix(" V")

        self._current = QDoubleSpinBox()
        self._current.setRange(0.0, 5.0)
        self._current.setDecimals(3)
        self._current.setSingleStep(0.1)
        self._current.setSuffix(" A")

        self._voltage.editingFinished.connect(
            lambda: self.voltageRequested.emit(self._voltage.value())
        )
        self._voltage_max = QPushButton("Max")
        self._voltage_max.setToolTip("Set voltage to the device's upper limit")
        self._voltage_max.clicked.connect(self._on_voltage_max)
        self._current.editingFinished.connect(
            lambda: self.currentRequested.emit(self._current.value())
        )

        self._output = QPushButton("Output OFF")
        self._output.setCheckable(True)
        self._output.setMinimumHeight(40)
        self._output.setStyleSheet(
            "QPushButton { font-weight: bold; }"
            f"QPushButton:checked {{ background: {theme.GREEN}; color: black; }}"
        )
        self._output.clicked.connect(self._on_output_clicked)

        voltage_row = QHBoxLayout()
        voltage_row.addWidget(self._voltage, stretch=1)
        voltage_row.addWidget(self._voltage_max)

        form = QFormLayout()
        form.addRow("Voltage:", voltage_row)
        form.addRow("Current:", self._current)

        layout = QHBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._output)

    def _on_output_clicked(self, checked: bool) -> None:
        self.outputRequested.emit(checked)

    def _on_voltage_max(self) -> None:
        self._voltage.setValue(self._voltage.maximum())
        self.voltageRequested.emit(self._voltage.value())

    def update_values(self, values: dict) -> None:
        # Don't fight the user while they are editing a spinbox.
        if "set_voltage" in values and not self._voltage.hasFocus():
            self._voltage.setValue(values["set_voltage"])
        if "set_current" in values and not self._current.hasFocus():
            self._current.setValue(values["set_current"])
        if "upper_limit_voltage" in values:
            self._voltage.setMaximum(values["upper_limit_voltage"])
        if "upper_limit_current" in values:
            self._current.setMaximum(values["upper_limit_current"])
        if "output_on" in values:
            on = values["output_on"]
            self._output.setChecked(on)
            self._output.setText("Output ON" if on else "Output OFF")

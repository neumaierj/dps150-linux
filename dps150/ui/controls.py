"""Setpoint controls and output switch."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
)


class ControlsPanel(QWidget):
    voltageRequested = Signal(float)
    currentRequested = Signal(float)
    outputRequested = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._voltage = QDoubleSpinBox()
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
        self._current.editingFinished.connect(
            lambda: self.currentRequested.emit(self._current.value())
        )

        self._output = QPushButton("Output OFF")
        self._output.setCheckable(True)
        self._output.setMinimumHeight(40)
        self._output.setStyleSheet(
            "QPushButton { font-weight: bold; }"
            "QPushButton:checked { background: #2e7d32; color: white; }"
        )
        self._output.clicked.connect(self._on_output_clicked)

        form = QFormLayout()
        form.addRow("Voltage:", self._voltage)
        form.addRow("Current:", self._current)

        layout = QHBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self._output)

    def _on_output_clicked(self, checked: bool) -> None:
        self.outputRequested.emit(checked)

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

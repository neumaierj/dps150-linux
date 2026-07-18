"""Live readout panel: output V/I/P, input voltage, temperature, CC/CV, alarms."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

_BIG = "font-size: 32pt; font-family: monospace; font-weight: bold;"
_BADGE = (
    "padding: 2px 10px; border-radius: 4px; font-weight: bold; color: white;"
)


class MeteringPanel(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._voltage = QLabel("--.---")
        self._current = QLabel("-.---")
        self._power = QLabel("--.--")
        for label in (self._voltage, self._current, self._power):
            label.setStyleSheet(_BIG)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._mode = QLabel("--")
        self._mode.setStyleSheet(_BADGE + "background: gray;")

        self._protection = QLabel()
        self._protection.setStyleSheet(
            "background: #c62828; color: white; font-weight: bold; padding: 6px;"
            "border-radius: 4px;"
        )
        self._protection.setAlignment(Qt.AlignCenter)
        self._protection.hide()

        self._input_voltage = QLabel("Input: --.- V")
        self._temperature = QLabel("Temp: --.- °C")

        grid = QGridLayout()
        for col, (value, unit) in enumerate(
            [(self._voltage, "V"), (self._current, "A"), (self._power, "W")]
        ):
            unit_label = QLabel(unit)
            unit_label.setStyleSheet("font-size: 16pt;")
            unit_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
            grid.addWidget(value, 0, col * 2)
            grid.addWidget(unit_label, 0, col * 2 + 1)

        info = QHBoxLayout()
        info.addWidget(self._mode)
        info.addStretch()
        info.addWidget(self._input_voltage)
        info.addWidget(self._temperature)

        layout = QVBoxLayout(self)
        layout.addWidget(self._protection)
        layout.addLayout(grid)
        layout.addLayout(info)

    def update_values(self, values: dict) -> None:
        if "output_voltage" in values:
            self._voltage.setText(f"{values['output_voltage']:.3f}")
        if "output_current" in values:
            self._current.setText(f"{values['output_current']:.3f}")
        if "output_power" in values:
            self._power.setText(f"{values['output_power']:.2f}")
        if "input_voltage" in values:
            self._input_voltage.setText(f"Input: {values['input_voltage']:.1f} V")
        if "temperature" in values:
            self._temperature.setText(f"Temp: {values['temperature']:.1f} °C")
        if "mode" in values:
            mode = values["mode"]
            color = "#ef6c00" if mode == "CC" else "#2e7d32"
            self._mode.setText(mode)
            self._mode.setStyleSheet(_BADGE + f"background: {color};")
        if "protection_state" in values:
            state = values["protection_state"]
            if state:
                self._protection.setText(f"⚠ Protection tripped: {state}")
                self._protection.show()
            else:
                self._protection.hide()

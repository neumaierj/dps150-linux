"""Device settings (brightness, volume, metering) and accumulated stats."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QWidget,
)

from .. import protocol


class SettingsPanel(QWidget):
    byteChanged = Signal(int, int)  # (register, value)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._brightness = QSpinBox()
        self._brightness.setRange(0, 10)
        self._brightness.editingFinished.connect(
            lambda: self.byteChanged.emit(protocol.BRIGHTNESS, self._brightness.value())
        )

        self._volume = QSpinBox()
        self._volume.setRange(0, 10)
        self._volume.editingFinished.connect(
            lambda: self.byteChanged.emit(protocol.VOLUME, self._volume.value())
        )

        self._metering = QCheckBox("Metering enabled")
        self._metering.clicked.connect(
            lambda checked: self.byteChanged.emit(
                protocol.METERING_ENABLE, 1 if checked else 0
            )
        )

        self._capacity = QLabel("-.--- Ah")
        self._energy = QLabel("-.--- Wh")

        form = QFormLayout(self)
        form.addRow("Display brightness:", self._brightness)
        form.addRow("Speaker volume:", self._volume)
        form.addRow(self._metering)
        form.addRow("Accumulated capacity:", self._capacity)
        form.addRow("Accumulated energy:", self._energy)

    def update_values(self, values: dict) -> None:
        if "brightness" in values and not self._brightness.hasFocus():
            self._brightness.setValue(values["brightness"])
        if "volume" in values and not self._volume.hasFocus():
            self._volume.setValue(values["volume"])
        if "metering_on" in values:
            self._metering.setChecked(values["metering_on"])
        if "output_capacity" in values:
            self._capacity.setText(f"{values['output_capacity']:.3f} Ah")
        if "output_energy" in values:
            self._energy.setText(f"{values['output_energy']:.3f} Wh")

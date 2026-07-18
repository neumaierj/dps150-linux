"""Editors for the five protection thresholds."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QWidget

from .. import protocol


class ProtectionPanel(QWidget):
    thresholdChanged = Signal(int, float)  # (register, value)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        form = QFormLayout(self)
        self._spins: dict[str, QDoubleSpinBox] = {}
        for key, register, label, maximum, suffix in (
            ("ovp", protocol.OVP, "Over-voltage (OVP):", 33.0, " V"),
            ("ocp", protocol.OCP, "Over-current (OCP):", 5.3, " A"),
            ("opp", protocol.OPP, "Over-power (OPP):", 165.0, " W"),
            ("otp", protocol.OTP, "Over-temperature (OTP):", 80.0, " °C"),
            ("lvp", protocol.LVP, "Low input voltage (LVP):", 30.0, " V"),
        ):
            spin = QDoubleSpinBox()
            spin.setRange(0.0, maximum)
            spin.setDecimals(1 if key in ("opp", "otp") else 2)
            spin.setSingleStep(0.1)
            spin.setSuffix(suffix)
            spin.editingFinished.connect(
                lambda reg=register, s=spin: self.thresholdChanged.emit(reg, s.value())
            )
            form.addRow(label, spin)
            self._spins[key] = spin

    def update_values(self, values: dict) -> None:
        for key, spin in self._spins.items():
            if key in values and not spin.hasFocus():
                spin.setValue(values[key])

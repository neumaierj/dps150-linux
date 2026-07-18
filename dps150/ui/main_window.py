"""Main window: connection bar, live metering, and output controls."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..device import DPS150, available_ports
from .controls import ControlsPanel
from .graph import GraphPanel
from .groups import GroupsPanel
from .metering import MeteringPanel
from .protection import ProtectionPanel
from .settings import SettingsPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DPS-150")

        self.device = DPS150(self)
        self.device.valuesChanged.connect(self._on_values)
        self.device.connectionChanged.connect(self._on_connection)

        self._ports = QComboBox()
        self._rescan = QPushButton("Rescan")
        self._rescan.clicked.connect(self._refresh_ports)
        self._connect = QPushButton("Connect")
        self._connect.clicked.connect(self._on_connect_clicked)

        connect_bar = QHBoxLayout()
        connect_bar.addWidget(QLabel("Port:"))
        connect_bar.addWidget(self._ports, stretch=1)
        connect_bar.addWidget(self._rescan)
        connect_bar.addWidget(self._connect)

        self.metering = MeteringPanel()
        self.controls = ControlsPanel()
        self.controls.voltageRequested.connect(self.device.set_voltage)
        self.controls.currentRequested.connect(self.device.set_current)
        self.controls.outputRequested.connect(self.device.set_output)

        self.groups = GroupsPanel()
        self.groups.setpointChanged.connect(self.device.set_float)
        self.groups.applyRequested.connect(self._on_apply_group)
        self.protection = ProtectionPanel()
        self.protection.thresholdChanged.connect(self.device.set_float)

        self.graph = GraphPanel()
        self.settings = SettingsPanel()
        self.settings.byteChanged.connect(self.device.set_byte)

        self._tabs = QTabWidget()
        self._tabs.addTab(self.graph, "Graph")
        self._tabs.addTab(self.groups, "Groups")
        self._tabs.addTab(self.protection, "Protection")
        self._tabs.addTab(self.settings, "Device")

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(connect_bar)
        layout.addWidget(self.metering)
        layout.addWidget(self.controls)
        layout.addWidget(self._tabs)
        layout.addStretch()
        self.setCentralWidget(central)

        self._device_info = QLabel("Not connected")
        self.statusBar().addPermanentWidget(self._device_info)
        self._info = {}

        self._set_panels_enabled(False)
        self._refresh_ports()

    def closeEvent(self, event) -> None:
        self.device.disconnect_from()
        super().closeEvent(event)

    def _refresh_ports(self) -> None:
        current = self._ports.currentData()
        self._ports.clear()
        for device, description in available_ports():
            self._ports.addItem(f"{device} — {description}", device)
        if current is not None:
            index = self._ports.findData(current)
            if index >= 0:
                self._ports.setCurrentIndex(index)

    def _on_connect_clicked(self) -> None:
        if self.device.is_connected:
            self.device.disconnect_from()
        elif self._ports.currentData() is not None:
            self.device.connect_to(self._ports.currentData())
        else:
            self.statusBar().showMessage("No serial port selected", 5000)

    def _on_connection(self, connected: bool, message: str) -> None:
        self._connect.setText("Disconnect" if connected else "Connect")
        self._ports.setEnabled(not connected)
        self._rescan.setEnabled(not connected)
        self._set_panels_enabled(connected)
        if connected:
            self.statusBar().showMessage(f"Connected to {message}", 5000)
        else:
            self._info.clear()
            self._device_info.setText("Not connected")
            if message:
                self.statusBar().showMessage(message, 10000)

    def _on_apply_group(self, volts: float, amps: float) -> None:
        self.device.set_voltage(volts)
        self.device.set_current(amps)

    def _on_values(self, values: dict) -> None:
        self.metering.update_values(values)
        self.controls.update_values(values)
        self.groups.update_values(values)
        self.protection.update_values(values)
        self.graph.update_values(values)
        self.settings.update_values(values)
        info_changed = False
        for key in ("model_name", "hardware_version", "firmware_version"):
            if key in values:
                self._info[key] = values[key].strip("\x00 ")
                info_changed = True
        if info_changed:
            self._device_info.setText(
                " ".join(
                    filter(
                        None,
                        (
                            self._info.get("model_name"),
                            self._info.get("hardware_version")
                            and f"HW {self._info['hardware_version']}",
                            self._info.get("firmware_version")
                            and f"FW {self._info['firmware_version']}",
                        ),
                    )
                )
            )

    def _set_panels_enabled(self, enabled: bool) -> None:
        self.metering.setEnabled(enabled)
        self.controls.setEnabled(enabled)
        self._tabs.setEnabled(enabled)

"""Rolling strip chart of output voltage, current and power."""

from __future__ import annotations

import csv
import time
from collections import deque

import pyqtgraph as pg
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import theme

_MAX_POINTS = 10_000  # ~15 min at the device's ~10 Hz metering rate


class GraphPanel(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._t0 = time.monotonic()
        self._t: deque[float] = deque(maxlen=_MAX_POINTS)
        self._v: deque[float] = deque(maxlen=_MAX_POINTS)
        self._i: deque[float] = deque(maxlen=_MAX_POINTS)
        self._p: deque[float] = deque(maxlen=_MAX_POINTS)
        self._capacity = 0.0
        self._energy = 0.0

        self._pause = QPushButton("Pause")
        self._pause.setCheckable(True)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear)
        export_csv = QPushButton("Export CSV…")
        export_csv.clicked.connect(self._export_csv)
        export_png = QPushButton("Export PNG…")
        export_png.clicked.connect(self._export_png)
        self._export_status = QLabel()
        self._export_status.setStyleSheet(f"color: {theme.MUTED};")

        # Horizontal legend instead of rotated axis labels: rotated text
        # overflows the plot rows whenever the window is short.
        legend = QLabel(
            f'<b><span style="color: {theme.YELLOW};">— Voltage / V</span>'
            f'&nbsp;&nbsp; <span style="color: {theme.CYAN};">— Current / A</span>'
            f'&nbsp;&nbsp; <span style="color: {theme.GREEN};">— Power / W</span></b>'
        )
        self._stats = QLabel("-.--- Ah   -.--- Wh")
        self._stats.setStyleSheet(f"color: {theme.MUTED}; font-weight: bold;")

        buttons = QHBoxLayout()
        buttons.addWidget(legend)
        buttons.addSpacing(16)
        buttons.addWidget(self._stats)
        buttons.addWidget(self._export_status, stretch=1)
        buttons.addWidget(export_csv)
        buttons.addWidget(export_png)
        buttons.addWidget(self._pause)
        buttons.addWidget(clear)

        graphs = pg.GraphicsLayoutWidget()
        self._graphs = graphs
        graphs.setBackground(theme.BACKGROUND)
        self._curves = []
        plots = []
        for row, color in enumerate((theme.YELLOW, theme.CYAN, theme.GREEN)):
            plot = graphs.addPlot(row=row, col=0)
            axis = plot.getAxis("left")
            # No SI rescaling: it rescales tick values and mislabels the axes.
            axis.enableAutoSIPrefix(False)
            axis.setWidth(56)
            plot.showGrid(x=True, y=True, alpha=0.3)
            plot.getAxis("bottom").enableAutoSIPrefix(False)
            if plots:
                plot.setXLink(plots[0])
            plots.append(plot)
            self._curves.append(plot.plot(pen=pg.mkPen(color, width=2)))
        for plot in plots[:-1]:
            plot.getAxis("bottom").setStyle(showValues=False)
        plots[-1].setLabel("bottom", "Time / s")

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(graphs)

    def update_values(self, values: dict) -> None:
        # Ah/Wh arrive as their own frames and stay live even while paused.
        if "output_capacity" in values:
            self._capacity = values["output_capacity"]
        if "output_energy" in values:
            self._energy = values["output_energy"]
        if "output_capacity" in values or "output_energy" in values:
            self._stats.setText(f"{self._capacity:.3f} Ah   {self._energy:.3f} Wh")
        # Register 195 always carries voltage, current and power together.
        if "output_voltage" not in values or self._pause.isChecked():
            return
        self._t.append(time.monotonic() - self._t0)
        self._v.append(values["output_voltage"])
        self._i.append(values["output_current"])
        self._p.append(values["output_power"])
        t = list(self._t)
        for curve, data in zip(self._curves, (self._v, self._i, self._p)):
            curve.setData(t, list(data))

    def clear(self) -> None:
        self._t0 = time.monotonic()
        for series in (self._t, self._v, self._i, self._p):
            series.clear()
        for curve in self._curves:
            curve.setData([], [])

    def _export_csv(self) -> None:
        if not self._t:
            self._export_status.setText("Nothing recorded yet")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export data", "", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["time_s", "voltage_V", "current_A", "power_W"])
                writer.writerows(zip(self._t, self._v, self._i, self._p))
        except OSError as e:
            self._export_status.setText(f"Export failed: {e}")
            return
        self._export_status.setText(f"Exported {len(self._t)} samples")

    def _export_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export image", "", "PNG (*.png)")
        if not path:
            return
        if self._graphs.grab().save(path, "PNG"):
            self._export_status.setText("Image exported")
        else:
            self._export_status.setText("Export failed")

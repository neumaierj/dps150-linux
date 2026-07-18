"""Rolling strip chart of output voltage, current and power."""

from __future__ import annotations

import time
from collections import deque

import pyqtgraph as pg
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

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

        self._pause = QPushButton("Pause")
        self._pause.setCheckable(True)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.clear)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self._pause)
        buttons.addWidget(clear)

        graphs = pg.GraphicsLayoutWidget()
        graphs.setBackground(theme.BACKGROUND)
        self._curves = []
        plots = []
        for row, (label, color) in enumerate(
            [
                ("Voltage / V", theme.YELLOW),
                ("Current / A", theme.CYAN),
                ("Power / W", theme.GREEN),
            ]
        ):
            plot = graphs.addPlot(row=row, col=0)
            plot.setLabel("left", label)
            plot.showGrid(x=True, y=True, alpha=0.3)
            if plots:
                plot.setXLink(plots[0])
            plots.append(plot)
            self._curves.append(plot.plot(pen=pg.mkPen(color, width=2)))
        plots[-1].setLabel("bottom", "Time / s")

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(graphs)

    def update_values(self, values: dict) -> None:
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
        for series in (self._t, self._v, self._i, self._p):
            series.clear()
        for curve in self._curves:
            curve.setData([], [])

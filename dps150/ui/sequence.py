"""Sequence tab: ramp generator, editable step table, CSV profiles, run/stop."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import sequence
from . import theme
from .controls import ClampSpinBox


class SequencePanel(QWidget):
    def __init__(self, runner: sequence.SequenceRunner, parent: QWidget | None = None):
        super().__init__(parent)
        self._runner = runner
        self._runner.stepStarted.connect(self._on_step_started)
        self._runner.finished.connect(self._on_finished)

        # Ramp generator form
        self._start_v = self._volt_spin(1.0)
        self._end_v = self._volt_spin(12.0)
        self._duration = QDoubleSpinBox()
        self._duration.setRange(0.1, 86400.0)
        self._duration.setValue(60.0)
        self._duration.setSuffix(" s")
        self._interval = QDoubleSpinBox()
        self._interval.setRange(0.1, 3600.0)
        self._interval.setValue(1.0)
        self._interval.setSuffix(" s")
        generate = QPushButton("Generate steps")
        generate.clicked.connect(self._on_generate)

        ramp_row = QHBoxLayout()
        for label, widget in (
            ("Ramp from", self._start_v),
            ("to", self._end_v),
            ("over", self._duration),
            ("every", self._interval),
        ):
            ramp_row.addWidget(QLabel(label))
            ramp_row.addWidget(widget)
        ramp_row.addWidget(generate)
        ramp_row.addStretch()

        # Step table
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Time / s", "Voltage / V", "Current / A"])
        self._table.horizontalHeader().setStretchLastSection(True)

        add_row = QPushButton("Add row")
        add_row.clicked.connect(lambda: self._table.insertRow(self._table.rowCount()))
        remove_row = QPushButton("Remove row")
        remove_row.clicked.connect(self._on_remove_row)
        load = QPushButton("Load CSV…")
        load.clicked.connect(self._on_load)
        save = QPushButton("Save CSV…")
        save.clicked.connect(self._on_save)

        table_buttons = QHBoxLayout()
        for button in (add_row, remove_row, load, save):
            table_buttons.addWidget(button)
        table_buttons.addStretch()

        # Run controls
        self._run = QPushButton("Run")
        self._run.setStyleSheet(
            f"QPushButton {{ font-weight: bold; color: {theme.GREEN}; }}"
        )
        self._run.clicked.connect(self._on_run)
        self._stop = QPushButton("Stop")
        self._stop.setStyleSheet(
            f"QPushButton {{ font-weight: bold; color: {theme.RED}; }}"
        )
        self._stop.setEnabled(False)
        self._stop.clicked.connect(self.stop)
        self._status = QLabel("Idle")
        self._status.setStyleSheet(f"color: {theme.MUTED};")

        run_row = QHBoxLayout()
        run_row.addWidget(self._run)
        run_row.addWidget(self._stop)
        run_row.addWidget(self._status, stretch=1)

        layout = QVBoxLayout(self)
        layout.addLayout(ramp_row)
        layout.addWidget(self._table)
        layout.addLayout(table_buttons)
        layout.addLayout(run_row)

        self._editors = (
            self._table, generate, add_row, remove_row, load,
            self._start_v, self._end_v, self._duration, self._interval,
        )
        self._steps: list[sequence.Step] = []
        self._max_voltage = sequence.MAX_VOLTAGE

    def update_values(self, values: dict) -> None:
        if "upper_limit_voltage" in values:
            self._max_voltage = values["upper_limit_voltage"]
            self._start_v.setMaximum(self._max_voltage)
            self._end_v.setMaximum(self._max_voltage)

    @staticmethod
    def _volt_spin(value: float) -> QDoubleSpinBox:
        spin = ClampSpinBox()
        spin.setRange(0.0, sequence.MAX_VOLTAGE)
        spin.setDecimals(3)
        spin.setValue(value)
        spin.setSuffix(" V")
        return spin

    # Table <-> steps

    def _set_table(self, steps: list[sequence.Step]) -> None:
        self._table.setRowCount(0)
        self._table.setRowCount(len(steps))
        for row, step in enumerate(steps):
            self._table.setItem(row, 0, QTableWidgetItem(f"{step.time_s:g}"))
            self._table.setItem(row, 1, QTableWidgetItem(f"{step.voltage:g}"))
            self._table.setItem(
                row, 2, QTableWidgetItem("" if step.current is None else f"{step.current:g}")
            )

    def _read_table(self) -> list[sequence.Step]:
        steps = []
        for row in range(self._table.rowCount()):
            cells = [self._table.item(row, col) for col in range(3)]
            texts = [c.text().strip() if c else "" for c in cells]
            if not any(texts):
                continue
            try:
                steps.append(
                    sequence.Step(
                        time_s=float(texts[0]),
                        voltage=float(texts[1]),
                        current=float(texts[2]) if texts[2] else None,
                    )
                )
            except ValueError:
                raise ValueError(f"row {row + 1}: not a number")
        sequence.validate(steps, max_voltage=self._max_voltage)
        return steps

    # Slots

    def _on_generate(self) -> None:
        try:
            steps = sequence.ramp_steps(
                self._start_v.value(),
                self._end_v.value(),
                self._duration.value(),
                self._interval.value(),
                max_voltage=self._max_voltage,
            )
        except ValueError as e:
            self._status.setText(str(e))
            return
        self._set_table(steps)
        self._status.setText(f"Generated {len(steps)} steps")

    def _on_remove_row(self) -> None:
        row = self._table.currentRow()
        self._table.removeRow(row if row >= 0 else self._table.rowCount() - 1)

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Load profile", "", "CSV (*.csv)")
        if not path:
            return
        try:
            steps = sequence.load_csv(path, max_voltage=self._max_voltage)
        except (OSError, ValueError) as e:
            self._status.setText(f"Load failed: {e}")
            return
        self._set_table(steps)
        self._status.setText(f"Loaded {len(steps)} steps")

    def _on_save(self) -> None:
        try:
            steps = self._read_table()
        except ValueError as e:
            self._status.setText(str(e))
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save profile", "", "CSV (*.csv)")
        if not path:
            return
        try:
            sequence.save_csv(path, steps)
        except OSError as e:
            self._status.setText(f"Save failed: {e}")
            return
        self._status.setText(f"Saved {len(steps)} steps")

    def _on_run(self) -> None:
        try:
            self._steps = self._read_table()
        except ValueError as e:
            self._status.setText(str(e))
            return
        self._run.setEnabled(False)
        self._stop.setEnabled(True)
        for widget in self._editors:
            widget.setEnabled(False)
        self._runner.start(self._steps, max_voltage=self._max_voltage)

    def stop(self) -> None:
        was_running = self._runner.is_running
        self._runner.stop()
        self._reset_controls()
        if was_running:
            self._status.setText("Stopped")

    def _on_step_started(self, index: int) -> None:
        step = self._steps[index]
        self._table.selectRow(index)
        self._status.setText(
            f"Step {index + 1}/{len(self._steps)}  t={step.time_s:g} s  "
            f"{step.voltage:g} V"
        )

    def _on_finished(self) -> None:
        self._reset_controls()
        self._status.setText(f"Finished ({len(self._steps)} steps)")

    def _reset_controls(self) -> None:
        self._run.setEnabled(True)
        self._stop.setEnabled(False)
        for widget in self._editors:
            widget.setEnabled(True)

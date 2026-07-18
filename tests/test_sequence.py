import pytest

from dps150 import sequence as s


def test_ramp_endpoints_and_spacing():
    steps = s.ramp_steps(1.0, 5.0, duration_s=4.0, interval_s=1.0)
    assert len(steps) == 5
    assert steps[0] == s.Step(0.0, 1.0)
    assert steps[-1] == s.Step(4.0, 5.0)
    assert [st.time_s for st in steps] == [0.0, 1.0, 2.0, 3.0, 4.0]
    assert [st.voltage for st in steps] == [1.0, 2.0, 3.0, 4.0, 5.0]
    assert all(st.current is None for st in steps)


def test_ramp_down():
    steps = s.ramp_steps(12.0, 3.0, duration_s=3.0, interval_s=1.0)
    assert steps[0].voltage == 12.0
    assert steps[-1].voltage == 3.0


def test_ramp_interval_longer_than_duration_gives_two_steps():
    steps = s.ramp_steps(0.0, 10.0, duration_s=2.0, interval_s=60.0)
    assert len(steps) == 2
    assert steps[0] == s.Step(0.0, 0.0)
    assert steps[-1] == s.Step(2.0, 10.0)


def test_ramp_rejects_bad_params():
    with pytest.raises(ValueError):
        s.ramp_steps(1.0, 5.0, duration_s=0, interval_s=1.0)
    with pytest.raises(ValueError):
        s.ramp_steps(1.0, 5.0, duration_s=5.0, interval_s=0)


def test_validate_rejects_bad_sequences():
    with pytest.raises(ValueError):
        s.validate([])
    with pytest.raises(ValueError):
        s.validate([s.Step(0.0, 1.0), s.Step(0.0, 2.0)])  # not increasing
    with pytest.raises(ValueError):
        s.validate([s.Step(-1.0, 1.0)])
    with pytest.raises(ValueError):
        s.validate([s.Step(0.0, 31.0)])  # voltage out of range
    with pytest.raises(ValueError):
        s.validate([s.Step(0.0, 1.0, current=6.0)])  # current out of range


def test_csv_roundtrip(tmp_path):
    path = str(tmp_path / "profile.csv")
    steps = [s.Step(0.0, 1.0, 0.5), s.Step(2.5, 3.3, None), s.Step(5.0, 12.0, 5.0)]
    s.save_csv(path, steps)
    assert s.load_csv(path) == steps


def test_load_csv_rejects_invalid(tmp_path):
    path = str(tmp_path / "bad.csv")
    path_obj = tmp_path / "bad.csv"
    path_obj.write_text("time_s,voltage_V,current_A\n0,1.0,\n0,2.0,\n")
    with pytest.raises(ValueError):
        s.load_csv(path)


def test_runner_plays_steps_in_order(qt_app):
    from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer

    runner = s.SequenceRunner()
    received = []
    runner.setVoltage.connect(lambda v: received.append(("V", round(v, 3))))
    runner.setCurrent.connect(lambda c: received.append(("I", round(c, 3))))
    done = []
    runner.finished.connect(lambda: done.append(True))

    steps = [
        s.Step(0.0, 1.0, 0.5),
        s.Step(0.05, 2.0),
        s.Step(0.1, 3.0),
    ]
    runner.start(steps)
    deadline = QTimer()
    loop = QEventLoop()
    runner.finished.connect(loop.quit)
    deadline.singleShot(2000, loop.quit)
    loop.exec()

    assert done, "sequence did not finish in time"
    assert received == [("V", 1.0), ("I", 0.5), ("V", 2.0), ("V", 3.0)]
    assert not runner.is_running


def test_runner_stop_halts(qt_app):
    from PySide6.QtCore import QEventLoop, QTimer

    runner = s.SequenceRunner()
    received = []
    runner.setVoltage.connect(received.append)
    runner.start([s.Step(0.0, 1.0), s.Step(10.0, 2.0)])

    loop = QEventLoop()
    QTimer.singleShot(100, loop.quit)
    loop.exec()
    runner.stop()
    assert received == [1.0]
    assert not runner.is_running

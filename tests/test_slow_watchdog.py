"""The slow-simulation watchdog: a crawling route is stopped and listed for rerun, never scored."""
import json
import subprocess
import sys

import pytest

import route_run
import score_routes
from route_run import (SLOW_STOP_REASON, SlowGuard, latest_simulation_seconds, run_evaluator, too_slow)


def test_never_stops_before_the_check_time():
    assert too_slow(0.0, 599.9) is False


def test_stops_below_the_minimum_factor_from_the_check_time():
    assert too_slow(5.9, 600) is True
    assert too_slow(100, 6000) is False  # exactly 0.01 is allowed
    assert too_slow(6.1, 600) is False


def test_route_still_loading_is_not_judged():
    assert too_slow(None, 5000) is False


def write_controls(path, *lines):
    path.write_text("".join(lines))


def test_latest_simulation_seconds_reads_the_last_complete_line(tmp_path):
    controls = tmp_path / "controls.jsonl"
    assert latest_simulation_seconds(controls) is None
    write_controls(controls)
    assert latest_simulation_seconds(controls) is None
    write_controls(controls, '{"simulation_seconds": 1.5}\n', '{"simulation_seconds": 3.0}\n')
    assert latest_simulation_seconds(controls) == 3.0


def test_partial_last_line_falls_back_to_the_previous_one(tmp_path):
    controls = tmp_path / "controls.jsonl"
    write_controls(controls, '{"simulation_seconds": 1.5}\n', '{"simulation_sec')
    assert latest_simulation_seconds(controls) == 1.5
    write_controls(controls, '{"step": 1}\n')
    assert latest_simulation_seconds(controls) is None


def test_guard_trips_on_a_slow_controls_file_using_an_injected_clock(tmp_path):
    controls = tmp_path / "controls.jsonl"
    write_controls(controls, '{"simulation_seconds": 2.0}\n')
    now = [0.0]
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], start_new_session=True)
    guard = SlowGuard(process, controls, check_after=600, every=3600, clock=lambda: now[0])
    try:
        assert guard.check() is False
        now[0] = 600
        assert guard.check() is True
        write_controls(controls, '{"simulation_seconds": 300.0}\n')
        assert guard.check() is False
    finally:
        guard.close()
        route_run.stop_process_group(process)


SLOW_EVALUATOR = (
    "import json, time\n"
    "open('controls.jsonl', 'w').write(json.dumps({'simulation_seconds': 0.01}) + '\\n')\n"
    "print('started', flush=True)\n"
    "while True:\n    print('tick', flush=True); time.sleep(0.2)\n")


def test_slow_stop_records_a_reason_and_the_route_goes_to_rerun(tmp_path, monkeypatch):
    output = tmp_path / "job" / "route-7"
    output.mkdir(parents=True)
    script = output / "slow.py"
    script.write_text(SLOW_EVALUATOR.replace("'controls.jsonl'", repr(str(output / "controls.jsonl"))))
    with pytest.raises(RuntimeError, match=SLOW_STOP_REASON):
        run_evaluator(output, [sys.executable, str(script)], {}, silence_limit_seconds=60,
                      slow_check_after_seconds=0.5, slow_check_every_seconds=0.2)
    marker = json.loads((output / "stop-reason.json").read_text())
    assert marker["reason"] == SLOW_STOP_REASON and marker["simulated_seconds"] == 0.01
    assert score_routes.stop_reason_of(output) == SLOW_STOP_REASON
    assert score_routes.chosen_attempt([output]) is None

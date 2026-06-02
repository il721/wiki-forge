import threading
from cockpit.jobs import JobRunner


def test_job_runs_and_returns_result(qtbot):
    runner = JobRunner()
    results = []
    runner.submit(lambda: 2 + 2, on_done=results.append)
    qtbot.waitUntil(lambda: results == [4], timeout=2000)


def test_job_runs_off_main_thread(qtbot):
    runner = JobRunner()
    main_id = threading.get_ident()
    seen = []
    runner.submit(threading.get_ident, on_done=seen.append)
    qtbot.waitUntil(lambda: len(seen) == 1, timeout=2000)
    assert seen[0] != main_id


def test_job_error_goes_to_on_error(qtbot):
    runner = JobRunner()
    errors = []

    def boom():
        raise RuntimeError("nope")

    runner.submit(boom, on_error=errors.append)
    qtbot.waitUntil(lambda: bool(errors) and "nope" in errors[0], timeout=2000)

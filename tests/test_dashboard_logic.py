from plugins.core.dashboard import run_gate_steps


def test_gate_stops_on_first_failure():
    calls = []

    def runner(args):
        calls.append(args)
        # 'lint' fails (returns code 1); later steps must not run.
        return (1, "lint error") if args == ["lint"] else (0, "ok")

    steps = [["doctor"], ["build"], ["lint"], ["source-lint"]]
    code, log = run_gate_steps(steps, runner)
    assert code == 1
    assert calls == [["doctor"], ["build"], ["lint"]]   # stopped after lint
    assert "FAILED" in log


def test_gate_runs_all_when_passing():
    def runner(args):
        return (0, "ok")
    steps = [["doctor"], ["build"]]
    code, log = run_gate_steps(steps, runner)
    assert code == 0
    assert "FAILED" not in log

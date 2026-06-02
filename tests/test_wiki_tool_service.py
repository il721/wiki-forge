from cockpit.jobs import JobRunner
from cockpit.wiki_tool_service import WikiToolService


def test_run_sync_invokes_vault_script(vault):
    svc = WikiToolService(JobRunner())
    code, text = svc.run_sync(vault, ["lint"])
    assert code == 0
    assert "STUB lint" in text


def test_run_sync_passes_multiple_args(vault):
    svc = WikiToolService(JobRunner())
    code, text = svc.run_sync(vault, ["source-scan", "--update"])
    assert "STUB source-scan --update" in text


def test_run_script_sync_runs_arbitrary_script(vault):
    (vault.root / "scripts" / "audit_public.py").write_text(
        "print('AUDIT OK')\n", encoding="utf-8")
    svc = WikiToolService(JobRunner())
    code, text = svc.run_script_sync(vault, "scripts/audit_public.py")
    assert code == 0
    assert "AUDIT OK" in text


def test_run_async_delivers_text(vault, qtbot):
    svc = WikiToolService(JobRunner())
    out = []
    svc.run(vault, ["doctor"], on_done=out.append)
    qtbot.waitUntil(lambda: bool(out) and "STUB doctor" in out[0], timeout=2000)

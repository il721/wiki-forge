"""Invoke a vault's own scripts as subprocesses and capture their output."""
import subprocess
import sys


class WikiToolService:
    def __init__(self, job_runner):
        self.jobs = job_runner

    def run_sync(self, vault, args):
        """Run `python <vault>/scripts/wiki_tool.py <args>`; return (code, text)."""
        cmd = [sys.executable, str(vault.script), *args]
        proc = subprocess.run(
            cmd, cwd=str(vault.root), capture_output=True, text=True
        )
        return proc.returncode, proc.stdout + proc.stderr

    def run_script_sync(self, vault, rel_script, args=()):
        """Run any script relative to the vault root; return (code, text)."""
        cmd = [sys.executable, str(vault.root / rel_script), *args]
        proc = subprocess.run(
            cmd, cwd=str(vault.root), capture_output=True, text=True
        )
        return proc.returncode, proc.stdout + proc.stderr

    def run(self, vault, args, on_done=None, on_error=None):
        """Async variant: delivers combined output text to on_done."""
        def work():
            _code, text = self.run_sync(vault, args)
            return text
        self.jobs.submit(work, on_done=on_done, on_error=on_error)

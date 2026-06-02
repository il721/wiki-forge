"""Dashboard plugin: health, counts, coverage, and the maintenance gate."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLabel

from cockpit.plugin import Plugin


def run_gate_steps(steps, runner):
    """Run (code, text) steps in order; stop at first non-zero. Pure/testable."""
    out = []
    for args in steps:
        code, text = runner(args)
        out.append(f"$ wiki_tool {' '.join(args)}\n{text}")
        if code != 0:
            out.append(f"GATE FAILED at: {' '.join(args)}")
            return code, "\n".join(out)
    return 0, "\n".join(out)


class DashboardPlugin(Plugin):
    id, name, version = "core.dashboard", "Dashboard", "1.0.0"

    GATE = [["doctor"], ["build"], ["lint"], ["source-lint"]]

    def activate(self, ctx):
        self.ctx = ctx
        w = QWidget()
        lay = QVBoxLayout(w)
        self.status = QLabel("No vault selected.")
        self.output = QPlainTextEdit(readOnly=True)
        lay.addWidget(self.status)
        lay.addWidget(self.output, 1)
        ctx.add_tab(w)

        ctx.add_toolbar_action("Doctor", lambda: self._single(["doctor"]))
        ctx.add_toolbar_action("Build", lambda: self._single(["build"]))
        ctx.add_toolbar_action("Lint", lambda: self._single(["lint"]))
        ctx.add_toolbar_action("Run maintenance gate", self._gate)

        ctx.on_vault_changed(self._on_vault)

    def _on_vault(self, vault):
        if vault is None:
            self.status.setText("No vault selected.")
        else:
            self.status.setText(f"Active vault: {vault.name}  ({vault.root})")
            self._single(["doctor"])

    def _single(self, args):
        if self.ctx.active_vault is None:
            return
        self.ctx.wiki_tool.run(*args, on_done=self.output.setPlainText)

    def _gate(self):
        if self.ctx.active_vault is None:
            return
        runner = lambda a: self.ctx.wiki_tool.run_sync(*a)
        self.ctx.run_job(
            lambda: run_gate_steps(self.GATE, runner)[1],
            on_done=self.output.setPlainText,
        )

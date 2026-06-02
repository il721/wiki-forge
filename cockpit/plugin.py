"""The public plugin contract: the base class and the context object.

Plugins depend ONLY on PluginContext. They never import the shell or each other.
"""


class Plugin:
    id = "unknown.plugin"
    name = "Unnamed"
    version = "0.0.0"

    def activate(self, ctx: "PluginContext") -> None:
        """Build UI and mount it via ctx. Called once at load."""

    def deactivate(self) -> None:
        """Optional cleanup (timers, threads)."""


class _WikiToolBinding:
    """Binds WikiToolService to whatever vault is currently active."""

    def __init__(self, service, active_provider):
        self._svc = service
        self._active = active_provider  # callable -> Vault

    def run(self, *args, on_done=None, on_error=None):
        self._svc.run(self._active(), list(args), on_done=on_done, on_error=on_error)

    def run_sync(self, *args):
        return self._svc.run_sync(self._active(), list(args))

    def run_script_sync(self, rel_script, *args):
        return self._svc.run_script_sync(self._active(), rel_script, list(args))


class PluginContext:
    """A plugin's entire API surface to the app."""

    def __init__(self, *, plugin, vault_manager, job_runner, wiki_tool,
                 llm, settings, log, ui):
        self.plugin = plugin
        self._vm = vault_manager
        self._jobs = job_runner
        self._llm = llm
        self._log = log
        self._ui = ui
        self.settings = settings  # per-plugin dict, persisted by the shell
        self.wiki_tool = _WikiToolBinding(wiki_tool, lambda: vault_manager.active)

    @property
    def active_vault(self):
        return self._vm.active

    def on_vault_changed(self, cb):
        self._vm.subscribe(cb)

    @property
    def llm(self):
        return self._llm

    def run_job(self, fn, on_done=None, on_error=None):
        self._jobs.submit(fn, on_done=on_done, on_error=on_error)

    def add_tab(self, widget):
        self._ui.add_tab(self.plugin, widget)

    def add_toolbar_action(self, label, fn):
        self._ui.add_toolbar_action(self.plugin, label, fn)

    def add_dashboard_card(self, widget):
        self._ui.add_dashboard_card(self.plugin, widget)

    def log(self, msg):
        self._log(msg)

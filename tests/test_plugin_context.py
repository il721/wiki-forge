from cockpit.config import JsonStore
from cockpit.jobs import JobRunner
from cockpit.vault import VaultManager
from cockpit.wiki_tool_service import WikiToolService
from cockpit.plugin import Plugin, PluginContext


class _FakeUi:
    def __init__(self):
        self.tabs = []
    def add_tab(self, plugin, widget):
        self.tabs.append((plugin.id, widget))
    def add_toolbar_action(self, plugin, label, fn):
        pass
    def add_dashboard_card(self, plugin, widget):
        pass


def _make_ctx(vault, tmp_path):
    vm = VaultManager(JsonStore(tmp_path / "vaults.json"))
    vm.add(vault.root)
    svc = WikiToolService(JobRunner())
    plugin = Plugin()
    plugin.id = "test.plugin"
    ui = _FakeUi()
    ctx = PluginContext(
        plugin=plugin, vault_manager=vm, job_runner=JobRunner(),
        wiki_tool=svc, llm=None, settings={}, log=lambda m: None, ui=ui,
    )
    return ctx, ui, vm


def test_context_exposes_active_vault(vault, tmp_path):
    ctx, _ui, vm = _make_ctx(vault, tmp_path)
    assert ctx.active_vault.root == vm.active.root


def test_context_on_vault_changed_fires(vault, tmp_path):
    ctx, _ui, vm = _make_ctx(vault, tmp_path)
    seen = []
    ctx.on_vault_changed(seen.append)
    vm.set_active(vm.active)
    assert len(seen) == 1


def test_wiki_tool_binding_uses_active_vault(vault, tmp_path, qtbot):
    ctx, _ui, _vm = _make_ctx(vault, tmp_path)
    code, text = ctx.wiki_tool.run_sync("lint")
    assert code == 0 and "STUB lint" in text


def test_add_tab_reaches_ui(vault, tmp_path):
    ctx, ui, _vm = _make_ctx(vault, tmp_path)
    sentinel = object()
    ctx.add_tab(sentinel)
    assert ui.tabs == [("test.plugin", sentinel)]

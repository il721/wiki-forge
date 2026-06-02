# Wiki-Forge

Desktop cockpit for managing Obsidian-based **LLM Wiki** vaults. It complements Obsidian
(your editor) with: a control panel over each vault's `scripts/wiki_tool.py`, an
LLM-assisted ingest/compile workspace (via local [Ollama](https://ollama.com)),
multi-vault switching, settings backup/restore, and a small **plugin system** where every
feature is a plugin built on one `PluginContext` API.

Built with **PySide6** (Qt for Python).

> ⚠️ **Under active construction.** The core services are in place and fully tested; the
> application shell and UI plugins are not built yet, so there is no launchable app
> command at this point. See **Status** below and `docs/PROGRESS.md` for the live state.

## Status

Built **task-by-task, TDD, one commit per task**. As of the latest commit:

| Layer | Module | State |
|-------|--------|-------|
| Config persistence | `cockpit/config.py` | ✅ |
| Vault model + registry | `cockpit/vault.py` | ✅ |
| Off-thread job runner | `cockpit/jobs.py` | ✅ |
| `wiki_tool.py` subprocess wrapper | `cockpit/wiki_tool_service.py` | ✅ |
| LLM provider contract + Ollama | `cockpit/llm/` | ✅ |
| Plugin contract (`Plugin`, `PluginContext`) | `cockpit/plugin.py` | ✅ |
| Plugin host (discovery + isolation) | `cockpit/plugin_host.py` | ✅ |
| Settings backup/restore | `cockpit/backup.py` | ⬜ next |
| App shell (`MainWindow`) | `cockpit/app.py` | ⬜ |
| Core plugins (Dashboard, LLM Settings, Ingest/Compile) | `plugins/` | ⬜ |

The full test suite passes (`pytest`). Tests mock Ollama — no running model is needed.

## Install

```bash
pip install -e ".[dev]"
```

This installs the package in editable mode plus the dev tools (pytest, pytest-qt).
PySide6 is a runtime dependency.

## Tests

```bash
pytest -v
```

## Architecture

- **Services** (`cockpit/`) are plain, UI-agnostic, individually tested modules:
  config storage, the `Vault`/`VaultManager` registry, a `JobRunner` for off-thread work,
  a subprocess wrapper around each vault's `wiki_tool.py`, and an Ollama LLM provider.
- **Plugins** depend on **only** `cockpit.plugin.PluginContext` — never on the shell or on
  each other. `PluginContext` is the entire API surface a plugin gets: the active vault,
  vault-change notifications, the wiki-tool binding, the LLM provider, a job runner, a log
  sink, and UI mount points (`add_tab` / `add_toolbar_action` / `add_dashboard_card`).
- **`PluginHost`** discovers `.py` files in the plugin dirs, instantiates each `Plugin`
  subclass, and **isolates failures** so one broken plugin can't take down the others.

### Writing a plugin (once the app shell lands)

Drop a `.py` file in the plugins directory exposing a `cockpit.plugin.Plugin` subclass and
restart Wiki-Forge:

```python
from cockpit.plugin import Plugin

class HelloPlugin(Plugin):
    id = "example.hello"
    name = "Hello"

    def activate(self, ctx):
        ctx.log(f"active vault: {ctx.active_vault.root}")
```

## Documentation

- **Design spec (why/what):** `docs/superpowers/specs/2026-05-29-wiki-forge-design.md`
- **Implementation plan (how, task-by-task):** `docs/superpowers/plans/2026-05-29-wiki-forge.md`
- **Live build status:** `docs/PROGRESS.md`

A polished end-user README and a manual smoke-test checklist land with the final task once
the app shell and core plugins are complete.

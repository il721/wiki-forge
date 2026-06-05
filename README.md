# Wiki-Forge

Desktop cockpit for managing Obsidian-based **LLM Wiki** vaults. It complements Obsidian
(your editor) with: a control panel over each vault's `scripts/wiki_tool.py`, local
[Ollama](https://ollama.com) integration, multi-vault switching, settings backup/restore,
and a small **plugin system** where every feature is a plugin built on one
`PluginContext` API.

Built with **PySide6** (Qt for Python).

## Install

```bash
cd wiki-forge
pip install -e ".[dev]"
```

This installs the package in editable mode plus the dev tools (pytest, pytest-qt).
PySide6 and requests are runtime dependencies.

## Run

```bash
wiki-forge          # console script, or:
python -m cockpit.app
```

The LLM features need [Ollama](https://ollama.com) running locally (default
`http://localhost:11434`). Everything else — vault switching, the maintenance gate,
backup/restore — works without it.

## What it does

- **Multi-vault switcher.** Register any number of LLM Wiki vaults and switch the active
  one from a dropdown; plugins react to the change.
- **Dashboard + maintenance gate.** Run `doctor` / `build` / `lint` against the active
  vault, or run the full gate (`doctor → build → lint → source-lint`) which stops at the
  first failure.
- **LLM Settings.** Point at an Ollama endpoint, check reachability, refresh the model
  list, and pick the model and temperature.
- **Settings backup/restore.** Zip the whole config directory and restore it from the
  File menu.

## Tests

```bash
pytest -v
```

The suite mocks Ollama and the `wiki_tool.py` subprocess, so no running model or real
vault is needed to run it.

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
- The **app shell** (`cockpit/app.py`) wires the services together, hosts the plugin tabs,
  and persists per-plugin settings (namespaced under `plugins.<id>` in `settings.json`).

The built-in features — Dashboard and LLM Settings — are themselves plugins under
`plugins/core/`, using the same public API any third-party plugin would.

### Writing a plugin

Drop a `.py` file in `~/.wiki-forge/plugins/` exposing a `cockpit.plugin.Plugin` subclass
and restart Wiki-Forge. See `plugins/core/dashboard.py` for a fuller reference.

```python
from cockpit.plugin import Plugin

class HelloPlugin(Plugin):
    id = "example.hello"
    name = "Hello"

    def activate(self, ctx):
        ctx.log(f"active vault: {ctx.active_vault.root if ctx.active_vault else None}")
```

## Manual smoke test

Run once against a real LLM Wiki vault with Ollama running:

- [ ] Launch `wiki-forge`; the window opens with Dashboard / LLM Settings tabs.
- [ ] **+ Add vault** → pick an existing LLM Wiki folder; it appears in the dropdown.
- [ ] Dashboard shows the active vault; **Run maintenance gate** streams
      doctor/build/lint/source-lint output and stops on any failure.
- [ ] LLM Settings → **Check / refresh models** shows "Reachable" and lists Ollama models.
- [ ] File → **Backup settings** writes a zip; **Restore settings** reads it back.

## Documentation

- **Design spec (why/what):** `docs/superpowers/specs/2026-05-29-wiki-forge-design.md`
- **Implementation plan (how, task-by-task):** `docs/superpowers/plans/2026-05-29-wiki-forge.md`
- **Live build status:** `docs/PROGRESS.md`

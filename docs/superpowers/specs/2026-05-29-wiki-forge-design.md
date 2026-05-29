# Wiki-Forge — Design Spec

**Date:** 2026-05-29
**Status:** Approved for planning
**Author:** brainstormed with Claude Code

## 1. Summary

**Wiki-Forge** is a desktop GUI "cockpit" (envelope) that sits on top of the existing
Obsidian-based **LLM Wiki** projects. It does **not** replace Obsidian (which stays the
note editor) — it orchestrates the deterministic tooling, drives a local LLM for
compiling sources, and manages multiple wiki vaults from one window.

The app is a **thin shell + plugins**. The shell owns no domain logic; it provides
services and UI mounting points. Every feature — including the built-in Dashboard,
Ingest, and LLM Settings — is a plugin using the same public `context` API, so new
functionality can be added later as small, self-contained plugin files without
rewriting the core.

### Confirmed scope (core)
- Control panel over `wiki_tool.py` (doctor / build / lint / source-scan / source-lint /
  source-coverage / audit) — the `AGENTS.md` maintenance gate as buttons.
- Ingest & compile workspace: raw sources → LLM-drafted Wiki notes (human-reviewed).
- Multi-vault switching (each vault = its own `Raw/` + `Wiki/` + `scripts/`).
- Local LLM processing via **Ollama**.
- Extensible: small, easy-to-write plugins.
- Simple backup/restore of program settings.

### Out of scope (explicitly)
- Replacing Obsidian as the editor/reader.
- In-app graph view, WYSIWYG markdown editing.
- RAG chat / semantic search — **deferred** as the natural first *plugin* once the core
  is solid (no shell changes needed to add it later).

## 2. Tech Stack
- **Language/UI:** Python + **PySide6** (Qt).
- **Local LLM:** **Ollama** HTTP API (`http://localhost:11434`), behind a swappable
  `LLMProvider` interface.
- **Wiki tooling:** each vault's own `scripts/wiki_tool.py`, invoked as a **subprocess**
  (left byte-for-byte untouched).
- **Backup:** stdlib `zipfile`.
- **Tests:** `pytest` against temporary fixture vaults + a mock HTTP server for Ollama.

## 3. Architecture

```
MainWindow (PySide6)
  - Vault switcher (shell chrome, top-left)
  - Tabbed plugin area: [Dashboard] [Ingest] [LLM] [future plugins...]
  - Log / Job dock (streamed output)
  - Menu: File -> Backup settings / Restore settings, Reload plugins

Shell services (the only "framework" code):
  - VaultManager   registry of vaults, active vault, persistence, vault_changed signal
  - JobRunner      runs slow work on a background thread; streams stdout/status to UI
  - LLMProvider    interface (generate / list_models / health); OllamaProvider impl
  - WikiToolService runs <vault>/scripts/wiki_tool.py as subprocess (cwd = vault.root)
  - PluginHost     discovers/loads plugins, builds context, mounts UI, isolates failures
```

**Golden rule:** anything slow (subprocess, LLM call, file scan) runs on the JobRunner
background thread. The UI thread only renders and reacts to signals — the window never
freezes.

### Why subprocess (not import) for wiki_tool
`wiki_tool.py` hard-codes its own `ROOT` (relative to its file location), so it cannot be
pointed at other vaults by import. Running each vault's own copy as a subprocess
(a) supports multi-vault cleanly, (b) keeps the deterministic tooling completely
untouched, and (c) reproduces the exact console output seen in the terminal today.

## 4. Plugin System

The contract: **a useful plugin is one small, focused file.** The shell discovers
plugins, hands each a `context` (its entire API to the app), and lets it mount UI.
Plugins depend only on `context` — never on each other or on shell internals.

### Discovery
On startup the `PluginHost` scans `plugins/` (bundled) and a user folder
`~/.wiki-forge/plugins/`. Each plugin is a `.py` file or package exposing a `Plugin`
subclass. Drop a file in and "Reload plugins" (or restart) — it appears. No central
registration list to edit.

### Plugin base class
```python
class Plugin:
    id = "unique.id"          # e.g. "core.dashboard"
    name = "Display Name"     # tab label
    version = "1.0.0"

    def activate(self, ctx: "PluginContext") -> None:
        """Called once when loaded. Build UI and mount it via ctx."""

    def deactivate(self) -> None:
        """Optional. Clean up timers/threads."""
```

### The `context` object (the public, versioned API)
| Member | Purpose |
|---|---|
| `ctx.active_vault` | Current vault: `.root`, `.raw_sources`, `.wiki`, `.name` (paths). |
| `ctx.on_vault_changed(fn)` | Register callback; fires when the active vault changes. |
| `ctx.wiki_tool.run(cmd, on_output=…, on_done=…)` | Run a `wiki_tool.py` command on the active vault (off-thread). |
| `ctx.llm.generate(prompt, model=…)` / `ctx.llm.list_models()` / `ctx.llm.health()` | Talk to the active LLM provider. |
| `ctx.run_job(fn, on_output=…, on_done=…)` | Run arbitrary slow work on the JobRunner. |
| `ctx.settings` | Dict auto-persisted per plugin (config remembered between runs). |
| `ctx.add_tab(widget)` | Mount a QWidget as the plugin's main tab. |
| `ctx.add_toolbar_action(label, fn)` | Add a toolbar button. |
| `ctx.add_dashboard_card(widget)` | Optionally contribute a card to the Dashboard. |
| `ctx.log(msg)` | Write to the shared log/job dock. |

### Reference plugin (complete, ~20 lines)
```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QPlainTextEdit
from cockpit.plugin import Plugin

class LintPlugin(Plugin):
    id, name, version = "extra.lint", "Quick Lint", "1.0.0"

    def activate(self, ctx):
        self.ctx = ctx
        w = QWidget(); lay = QVBoxLayout(w)
        self.out = QPlainTextEdit(readOnly=True)
        btn = QPushButton("Run lint on active vault")
        btn.clicked.connect(self._lint)
        lay.addWidget(btn); lay.addWidget(self.out)
        ctx.add_tab(w)

    def _lint(self):
        self.ctx.wiki_tool.run("lint", on_done=self.out.setPlainText)
```

### Guarantees
- **One dependency direction:** plugins → `context` → shell.
- **Built-ins prove the API:** Dashboard, Ingest, LLM Settings are themselves plugins.
- **Failure isolation:** an exception during `activate()` is caught, logged with traceback,
  and that plugin is skipped — the app and other plugins still start.
- **Versioned context:** `context` is the only contract; shell internals can evolve freely.

## 5. Built-in Modules

All three ship in `plugins/core/` and serve as reference plugins.

### Vault Switcher (shell chrome, not a plugin)
- Dropdown of registered vaults; switching sets active vault and fires `vault_changed`.
- **+ Add vault** → folder picker; validates presence of `Raw/`, `Wiki/`,
  `scripts/wiki_tool.py` before accepting. Persists to `vaults.json`.
- Context menu: remove / open in file explorer / open in Obsidian.

### 1. Dashboard `core.dashboard`
On vault change, runs `doctor` and reads `catalog.jsonl` / `source-manifest.jsonl`, then
shows cards:
- **Health** — folder + Python checks (parsed from `doctor`).
- **Counts** — Raw sources vs compiled notes (Topics/Concepts/Entities/Projects/Logs).
- **Coverage** — covered vs uncovered sources (from `source-coverage`); uncovered listed.
- **Lint status** — green, or a clickable list of `lint` / `source-lint` errors.

**Commit-gate toolbar:** one button each for `doctor` / `build` / `lint` / `source-lint` /
`audit_public.py`, plus **"Run full maintenance gate"** which chains them in order,
streaming output to the dock and **stopping on the first non-zero exit** (mirrors the
`.githooks/pre-commit` ritual in `AGENTS.md`).

### 2. Ingest & Compile `core.ingest`
- **Left:** list of `Raw/Sources/*.md`, each tagged **unprocessed / processed / covered**
  (from `source-scan` + coverage map).
- **Center:** selected source content + parsed frontmatter.
- **Action — "Compile with LLM":** sends the source through Ollama using a compile prompt
  + chosen note template + `frontmatter-schema`; drafts one or more Wiki notes with
  `sources=[raw path]` and `source_count` pre-filled.
- User **reviews** the draft, picks the target folder, and saves into `Wiki/<Folder>/`.
  Deeper editing happens in Obsidian.
- After saving, one-click **"Update manifest"** runs
  `source-scan --update --accept-covered` then `source-lint`; the source flips to
  **covered**.

The LLM only **drafts**; writes are explicit and verified by the deterministic tooling.
Nothing is auto-committed.

### 3. LLM Settings `core.llm`
- Ollama endpoint URL + **health check**; model picker (`list_models`); separate
  **default model** for *compile* vs *chat*; temperature / max-tokens.
- **Editable prompt templates** (compile prompt seeded from existing `Prompts.md` /
  `PROMPTS_for_LLM_Wiki_*` files) — tune compilation without touching code.

> A future **RAG chat** plugin slots in as a 4th tab using `ctx.llm` + Pinecone sync,
> with no shell changes.

## 6. Data Flow

**A. Startup** — load `vaults.json` → build `VaultManager` → `MainWindow` →
`PluginHost` scans plugin folders → instantiate + `activate(ctx)` + mount → set last-used
active vault → emit `vault_changed` → plugins render.

**B. Switch vault** — switcher → `VaultManager.set_active()` (persist last used) →
emit `vault_changed` → each plugin re-derives state from `ctx.active_vault` (no stale paths).

**C. Run wiki_tool command** — button → `ctx.wiki_tool.run("lint", …)` →
`WikiToolService` builds `python <vault>/scripts/wiki_tool.py lint` (cwd = vault.root) →
`JobRunner` spawns subprocess on worker thread → stdout streamed to dock → exit code +
text returned via signal. The full gate queues `doctor → build → lint → source-lint →
audit`, halting on first non-zero exit.

**D. Compile-with-LLM** — select source → read file + frontmatter → load compile prompt +
note template + schema → `ctx.llm.generate(...)` (JobRunner → Ollama HTTP) → stream tokens
to draft pane → parse into Wiki note(s), pre-fill `sources` / `source_count` → user reviews
+ picks folder → save under `Wiki/` → optional `source-scan --update --accept-covered` +
`source-lint` → source flips to covered.

**E. Persistence**
| Location | Holds | Owner |
|---|---|---|
| `~/.wiki-forge/vaults.json` | registered vaults + last active | VaultManager |
| `~/.wiki-forge/settings.json` | Ollama URL, default models, per-plugin `ctx.settings` | shell |
| `~/.wiki-forge/plugins/` | user-added plugins | PluginHost |
| inside each vault | all notes, catalog, manifest — **unchanged** | `wiki_tool.py` |

App config lives **outside** the vaults, so vaults stay clean and git-safe (no cockpit
state leaks into a repo or trips `audit_public.py`).

## 7. Backup & Restore (settings)

Shell menu actions: **File → Backup settings… / Restore settings…**

- **Backup:** zip the entire `~/.wiki-forge/` folder (vaults.json + settings.json +
  per-plugin settings + user plugins) to a user-chosen, timestamped file
  (`wiki-forge-backup-YYYY-MM-DD.zip`). Uses stdlib `zipfile`.
- **Restore:** pick a backup zip → confirm prompt → unzip back into `~/.wiki-forge/`
  (overwriting current settings) → reload.
- **Not included:** vault note content (those are the user's notes, version-controlled in
  each vault's own git).

## 8. Error Handling

The cockpit never crashes from a vault problem, a bad plugin, or an offline LLM — it
reports and keeps running.

- **Plugin load failure** — caught per-plugin, logged with traceback, plugin skipped;
  app + other plugins start normally.
- **wiki_tool failures** — expected signal, not crashes. Non-zero exit shown as red status
  + captured output in the dock. Gate chain stops at first failure and names the step.
- **Invalid/missing vault** — flagged in switcher; actions disabled with a locate/remove
  prompt rather than erroring mid-run.
- **Ollama offline / model missing** — `health()` checked before compile; Compile disabled
  with inline hint. Mid-generation drop surfaces as a dock error; draft pane keeps streamed
  text.
- **Never silent, never destructive** — every LLM draft is reviewed before any write; no
  auto-commit, no overwrite without confirmation. Writes go only under `Wiki/`; `Raw/` is
  never modified (matches `AGENTS.md`).

## 9. Testing

Logic is concentrated in shell services (plugins stay thin), so tests target services:

- **Unit (pytest, temp fixture vault** — copy the `tutorial/` structure into a temp dir**):**
  - `VaultManager` — register/validate/switch/persist.
  - `WikiToolService` — real subprocess on fixture; assert parsed `doctor`/`build`/`lint`.
  - `OllamaProvider` — against a **mock HTTP server** (no live model in CI).
  - `JobRunner` — work runs off-thread; signals fire.
  - Backup/Restore — round-trip a temp config dir.
- **Plugin host** — load a good dummy plugin and a throwing dummy plugin; assert the bad one
  is skipped and the good one mounts.
- **Manual smoke checklist** — switch vaults, run the gate, compile one fixture source
  end-to-end with a real local model.

UI widget testing kept light (PySide6 GUI tests are brittle); logic lives in headless-
testable services.

## 10. Proposed Project Layout
```
wiki-forge/
  cockpit/
    __init__.py
    app.py                # entry point, MainWindow
    plugin.py             # Plugin base class + PluginContext
    plugin_host.py        # discovery, load, isolation, UI mounting
    vault.py              # Vault model + VaultManager
    jobs.py               # JobRunner (QThread/QThreadPool)
    wiki_tool_service.py  # subprocess wrapper
    llm/
      base.py             # LLMProvider interface
      ollama.py           # OllamaProvider
    config.py             # ~/.wiki-forge persistence
    backup.py             # zip/unzip settings
  plugins/
    core/
      dashboard.py
      ingest.py
      llm_settings.py
  tests/
    fixtures/             # temp vault scaffolding
    test_vault.py
    test_wiki_tool_service.py
    test_ollama.py
    test_jobs.py
    test_plugin_host.py
    test_backup.py
  pyproject.toml
  README.md
```

## 11. Open Questions (for the plan phase)
- Packaging: run from source vs PyInstaller bundle (decide during planning).
- Whether "Reload plugins" hot-reloads or requires restart (start with restart; hot-reload
  optional later).

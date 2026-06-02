# Wiki-Forge — Build Progress

_Updated and committed at the end of every task. This is the quick "where are we" file._

## Status: IN PROGRESS — Tasks 1-10 done, next is Task 11

> **Source of truth for resume = this file's "Next action" + `git log`.** Pick up there.

| # | Task | State |
|---|------|-------|
| 1 | Project scaffold + pytest harness | ✅ done (`1ee7eed`) |
| 2 | `config.py` (config_dir + JsonStore) | ✅ done (`6cd7a06`) |
| 3 | `vault.py` (Vault + VaultManager) | ✅ done (`4305649`) |
| 4 | `jobs.py` (JobRunner) | ✅ done (`4ce19d9`) |
| 5 | `wiki_tool_service.py` (subprocess wrapper) | ✅ done (`112b05a`) |
| 6 | `llm/` (provider contract + Ollama) | ✅ done (`4b7761d`) |
| 7 | `plugin.py` (Plugin + PluginContext) | ✅ done (`16ca671`) |
| 8 | `plugin_host.py` (discovery + isolation) | ✅ done (`fbe53f4`) |
| 9 | `backup.py` (settings backup/restore) | ✅ done (`b212049`) |
| 10 | `app.py` (MainWindow shell) | ✅ done (`d154074`) |
| 11 | Dashboard + LLM Settings plugins | ⬜ todo |
| 12 | Ingest & Compile plugin | ⬜ todo |
| 13 | README + manual smoke checklist | ⬜ todo |

## Next action
Begin **Task 11** (core plugins: `plugins/core/dashboard.py` + `plugins/core/llm_settings.py`):
the Dashboard plugin (health/counts/coverage + maintenance gate) and the LLM Settings
plugin. TDD starts with a PURE logic test `tests/test_dashboard_logic.py` for
`run_gate_steps(steps, runner)` (runs steps in order, stops at first non-zero, log
contains "FAILED"). NOTE: if `plugins` isn't importable as a package, create empty
`plugins/__init__.py` and `plugins/core/__init__.py` first (plan Task 11 Step 2 note).
The Qt plugin classes subclass `cockpit.plugin.Plugin` and mount via `ctx` (add_tab,
add_toolbar_action, on_vault_changed, run_job, wiki_tool.run/run_sync). See plan Task 11.
Working dir `F:\____IL_AI\wiki-forge`, branch `build/wiki-forge`. Drop the `wiki-forge/`
path prefix (root IS the project). Once Task 11+12 add the three core plugins, tighten
`tests/test_app_smoke.py` to assert the Dashboard/Ingest/LLM Settings tabs (plan Task 12
Step 4).

## Environment notes
- Python: environment default `python` / `pip` (no venv; using global site-packages).
- `pip install -e ".[dev]"`: DONE. PySide6 6.11.1 already present; installed
  pytest 9.0.3, pytest-qt 4.5.0.
- Ollama: only needed for the final manual smoke test (Task 13).

## Log
- Task 1 (`1ee7eed`): scaffolded pyproject.toml, cockpit/ + cockpit/llm/ + tests/
  package markers, tests/test_smoke.py. `pytest` 1 passed. Verified independently.
- Task 2 (`6cd7a06`): cockpit/config.py (config_dir + JsonStore) + tests/test_config.py.
  TDD followed; 2 passed. Verified independently.
- Task 3 (`4305649`): cockpit/vault.py (Vault + VaultManager observer) +
  tests/conftest.py (vault fixture) + tests/test_vault.py. TDD; full suite 8 passed.
- Task 4 (`4ce19d9`): cockpit/jobs.py (JobRunner + _Worker/_WorkerSignals) +
  tests/test_jobs.py. TDD; full suite 11 passed. Two justified deviations from the
  plan text: (1) `_Worker.setAutoDelete(False)` — without it QThreadPool frees the
  worker/signals before the queued cross-thread signal is delivered (plan's own
  off-thread test would flake). Known tradeoff: workers aren't auto-reaped — revisit
  only if a session ever submits huge job volumes. (2) test uses `bool(errors)` since
  pytest-qt 4.5 `waitUntil` rejects non-bool/None returns; semantics unchanged.
- Task 5 (`112b05a`): cockpit/wiki_tool_service.py (WikiToolService: run_sync /
  run_script_sync / async run via JobRunner) + tests/test_wiki_tool_service.py. TDD;
  full suite 15 passed. Matches plan verbatim (test uses `bool(out)` per convention).
- Task 6 (`4b7761d`): cockpit/llm/base.py (LLMProvider ABC) + cockpit/llm/ollama.py
  (OllamaProvider: health/list_models/generate) + tests/test_ollama.py. TDD; full suite
  19 passed. Matches plan verbatim; tests monkeypatch requests (no live Ollama).
- Task 7 (`16ca671`): cockpit/plugin.py (Plugin base class + _WikiToolBinding +
  PluginContext DI surface) + tests/test_plugin_context.py. TDD; full suite 23 passed.
  Matches plan verbatim. Two-stage review (spec compliance + code quality) both passed.
  Reviewer note: the high-level spec mentions an `on_output=` callback on run_job /
  wiki_tool.run that the plan's Task 7 code omits (uses on_done/on_error only) — that's
  a plan-level design decision, not an implementation gap; revisit if streaming output
  is needed by a later plugin task.
- Task 8 (`fbe53f4`): cockpit/plugin_host.py (PluginHost: discover/load_all with
  per-plugin failure isolation) + tests/test_plugin_host.py. TDD; full suite 25 passed.
  Matches plan verbatim. Two-stage review both passed. Known minor coverage gap (carried
  from plan): no test for an import-time explosion (only the `_`-prefix skip path is
  tested) and no test for a missing plugin dir — both low-risk straightforward branches.
- Task 9 (`b212049`): cockpit/backup.py (backup_settings zips the whole config dir with
  ZIP_DEFLATE, posix relative paths; restore_settings extracts a zip to a target dir) +
  tests/test_backup.py (roundtrip: settings.json value + nested plugins/extra.py survive).
  TDD; full suite 26 passed. Matches plan verbatim. Two-stage review both passed.
  Reviewer notes (informational, in-scope-minimal): restore merges rather than clears the
  target dir, and no missing-zip / path-traversal hardening — revisit if a restore needs
  clean-slate semantics or untrusted archives are ever supported.
- Task 10 (`d154074`): cockpit/app.py (MainWindow shell: wires config/JsonStore +
  VaultManager + JobRunner + WikiToolService + OllamaProvider, a `_UiHost` adapter for
  plugin mounts, vault-switcher combo, toolbar, log dock, File menu backup/restore/reload;
  per-plugin settings under `plugins.<id>`, saved on close) + tests/test_app_smoke.py
  (uses the SIMPLER `test_mainwindow_constructs` body per plan — asserts `win.tabs` exists;
  the 3-core-plugin assertion is deferred to Task 12 since those plugins don't exist yet).
  TDD; full suite 27 passed. Matches plan verbatim. Two-stage review both passed.
  Reviewer notes (non-blocking, code is verbatim plan): (1) `config_dir()` is called a 2nd
  time for the plugin dir instead of reusing the captured `cfg` — harmless redundancy;
  (2) `_refresh_vault_combo` re-fires `set_active` on every refresh (incl. after adding a
  vault), not only on init — fine now, but revisit if a later plugin's `on_vault_changed`
  handler is expensive. Verified PluginHost.discover() skips the not-yet-existing
  plugins/core dir, so the shell loads cleanly standalone.

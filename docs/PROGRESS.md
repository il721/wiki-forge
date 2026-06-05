# Wiki-Forge — Build Progress

_Updated and committed at the end of every task. This is the quick "where are we" file._

## Status: CODE-COMPLETE — Tasks 1-13 built; only the Task 13 manual smoke run (user) remains

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
| 11 | Dashboard + LLM Settings plugins | ✅ done (`1eb81ab`) |
| 12 | ~~Ingest & Compile plugin~~ | ❌ removed (feature dropped — sources added in Obsidian) |
| 13 | README + manual smoke checklist | ✅ README done (`2f8053d`); ⬜ manual smoke = user |

## Next action
All 13 tasks are BUILT. The only thing left in the plan is **Task 13 Step 2 — the manual
smoke checklist — which is a USER action** (needs a running app, a real LLM Wiki vault,
and a live Ollama): launch `wiki-forge`, add a vault, run the maintenance gate,
check/refresh models, backup/restore. The checklist lives in
`README.md` (and plan Task 13 Step 2). Once the user has run it and is satisfied, the
branch `build/wiki-forge` is feature-complete → use
**superpowers:finishing-a-development-branch** to decide merge vs PR vs cleanup
(currently unmerged on `build/wiki-forge`; main is `main`). Working dir
`F:\____IL_AI\wiki-forge`.

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
- Task 11 (`1eb81ab`): plugins/core/dashboard.py (pure `run_gate_steps` + DashboardPlugin:
  status/output tab, doctor/build/lint toolbar actions, off-thread maintenance gate) +
  plugins/core/llm_settings.py (LlmSettingsPlugin: Ollama URL/model/temp form + health
  check + save) + empty plugins/__init__.py & plugins/core/__init__.py + tests/
  test_dashboard_logic.py (2 tests for run_gate_steps). TDD; full suite 29 passed — the
  app smoke test stayed green (PluginHost now actually discovers & loads both plugins).
  Matches plan verbatim. Two-stage review both passed. KNOWN FOLLOW-UP (code-quality
  reviewer, Important but non-blocking, code is verbatim plan): LlmSettingsPlugin._check
  calls `ctx.llm.health()` synchronously on the UI thread (up to ~5s freeze on a bad
  network) while the very next list_models call IS off-threaded via run_job — wrap health()
  in run_job too if it ever bites. Minor notes: `chat_model` setting is defaulted but never
  written by _save (no form row yet); _single discards the exit code (no status flag on a
  single failed action). All in-scope-minimal per the plan.
- Task 12 (`cd9f5eb`, + fix `6050b1d`): plugins/core/ingest.py (pure `build_wiki_note` —
  schema-correct YAML frontmatter + body — and IngestPlugin: two-pane tab, raw-source list,
  LLM compile draft, review, save-to-Wiki + `source-scan --update --accept-covered`) +
  tests/test_ingest_logic.py (1 test) + tightened tests/test_app_smoke.py to assert all 3
  core-plugin tabs (Dashboard/Ingest/LLM Settings) load. TDD; full suite 30 passed. Matches
  plan verbatim. Two-stage review passed. The code-quality review caught a REAL runtime bug
  in the plan's verbatim _save: it wrote to `Wiki/<tag-folder>/` without creating it, and
  `Vault.is_valid()` only guarantees `Wiki/` exists — so the first save to a tag folder on a
  fresh vault raised FileNotFoundError. Fixed in `6050b1d` with a one-line
  `dest_dir.mkdir(parents=True, exist_ok=True)` (justified deviation from plan; the manual
  smoke test in Task 13 exercises exactly this path). The mkdir is covered only by the smoke
  path, not a dedicated unit test (Qt _save is not unit-tested, consistent with project
  altitude). Other reviewer notes (non-blocking, verbatim plan): _compile runs ollama
  health() synchronously on the UI thread (same as Task 11); no guard against saving the
  "Compiling…" placeholder; _reload_sources is top-level glob only.
- Task 13 (`2f8053d`): replaced the interim README (`bf3efdf`) with the finished
  user-facing README.md — Install / Run (`wiki-forge` console script or `python -m
  cockpit.app`, both verified to exist in pyproject + app.main) / What-it-does / Tests /
  Architecture / Writing-a-plugin / Manual-smoke-test / Documentation. Reconciled rather
  than duplicated: kept the richer Architecture + plugin sections from the interim version,
  dropped the under-construction warning and the stale status table. Step 2 (manual smoke
  run) is left UNCHECKED in the plan — it's a user action requiring a real vault + Ollama.
- Post-build enhancement — Modern Dark theme (`833fd48`, spec `05fc75b`): visual-only restyle
  per the user's DESIGN.md. New `cockpit/theme.py` (centralized QSS + bundled Lexend-Light.ttf
  under cockpit/assets/fonts/, SIL OFL) applied once in `app.main()` via `apply_theme(app)`;
  one-line wiring in app.py, no structural change. tests/test_theme.py (3 tests). Full suite
  33 passed. Adapted DESIGN.md font sizes down for the dense cockpit; icons deferred. Spec:
  docs/superpowers/specs/2026-06-02-wiki-forge-dark-theme-design.md.
- Post-build removal — Ingest & Compile plugin dropped: deleted plugins/core/ingest.py and
  tests/test_ingest_logic.py, and updated tests/test_app_smoke.py to assert the tab is gone.
  Rationale: sources are now added to the wiki directly inside Obsidian, so the in-cockpit
  ingest/compile workspace was unneeded. `Vault.raw_sources` kept (general vault property).
  Full suite 33 passed.

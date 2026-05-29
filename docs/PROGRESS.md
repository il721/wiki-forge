# Wiki-Forge — Build Progress

_Updated and committed at the end of every task. This is the quick "where are we" file._

## Status: IN PROGRESS — Tasks 1-3 done, next is Task 4

> **Source of truth for resume = this file's "Next action" + `git log`.** Pick up there.

| # | Task | State |
|---|------|-------|
| 1 | Project scaffold + pytest harness | ✅ done (`1ee7eed`) |
| 2 | `config.py` (config_dir + JsonStore) | ✅ done (`6cd7a06`) |
| 3 | `vault.py` (Vault + VaultManager) | ✅ done (`4305649`) |
| 4 | `jobs.py` (JobRunner) | ⬜ todo |
| 5 | `wiki_tool_service.py` (subprocess wrapper) | ⬜ todo |
| 6 | `llm/` (provider contract + Ollama) | ⬜ todo |
| 7 | `plugin.py` (Plugin + PluginContext) | ⬜ todo |
| 8 | `plugin_host.py` (discovery + isolation) | ⬜ todo |
| 9 | `backup.py` (settings backup/restore) | ⬜ todo |
| 10 | `app.py` (MainWindow shell) | ⬜ todo |
| 11 | Dashboard + LLM Settings plugins | ⬜ todo |
| 12 | Ingest & Compile plugin | ⬜ todo |
| 13 | README + manual smoke checklist | ⬜ todo |

## Next action
Begin **Task 4** (`jobs.py`): TDD `JobRunner` (Qt threadpool, off-thread work with
on_done/on_error signals). Tests use the `qtbot` fixture from pytest-qt. See plan Task 4.
Working dir `F:\____IL_AI\wiki-forge`, branch `build/wiki-forge`. Remember: drop the
`wiki-forge/` path prefix from the plan (root IS the project).

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

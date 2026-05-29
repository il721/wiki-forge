# Wiki-Forge — Build Progress

_Updated and committed at the end of every task. This is the quick "where are we" file._

## Status: IN PROGRESS — Task 1 done, next is Task 2

> **Source of truth for resume = this file's "Next action" + `git log`.** Pick up there.

| # | Task | State |
|---|------|-------|
| 1 | Project scaffold + pytest harness | ✅ done (`1ee7eed`) |
| 2 | `config.py` (config_dir + JsonStore) | ⬜ todo |
| 3 | `vault.py` (Vault + VaultManager) | ⬜ todo |
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
Begin **Task 2** (`config.py`): TDD `config_dir()` + `JsonStore` per the plan.
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

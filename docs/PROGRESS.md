# Wiki-Forge — Build Progress

_Updated and committed at the end of every task. This is the quick "where are we" file._

## Status: NOT STARTED — ready to begin Task 1

| # | Task | State |
|---|------|-------|
| 1 | Project scaffold + pytest harness | ⬜ todo |
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
Begin **Task 1**: create `pyproject.toml`, package markers, `tests/test_smoke.py`,
then `pip install -e ".[dev]"` and `pytest tests/test_smoke.py -v`.

## Environment notes
- Python: use the environment's default `python` / `pip`.
- venv: _not yet created_ (decide at Task 1; PySide6 is large).
- `pip install -e ".[dev]"`: _not yet run_.
- Ollama: only needed for the final manual smoke test (Task 13).

## Log
- _(empty — first task not yet done)_

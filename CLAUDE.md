# Wiki-Forge — Agent Orientation

Wiki-Forge is a **PySide6 desktop cockpit** for managing Obsidian-based **LLM Wiki**
vaults. It complements Obsidian (the user's editor) with: a control panel over each
vault's `scripts/wiki_tool.py`, an LLM-assisted ingest/compile workspace (via local
**Ollama**), multi-vault switching, settings backup, and a small **plugin system**
(every feature is a plugin using one `PluginContext` API).

## Source of truth
- **Spec (why/what):** `docs/superpowers/specs/2026-05-29-wiki-forge-design.md`
- **Plan (how, task-by-task):** `docs/superpowers/plans/2026-05-29-wiki-forge.md`
- **Live status:** `docs/PROGRESS.md`

> Note: the plan was written with a nested `wiki-forge/` path prefix. The project root
> **is** `wiki-forge`, so drop that prefix — code lives at `cockpit/`, `plugins/`,
> `tests/`, `pyproject.toml` directly. Do **not** create a nested `wiki-forge/wiki-forge`.

## How to work / resume this project
This is being built **task-by-task, TDD, one commit per task**, using
`superpowers:subagent-driven-development` (fresh subagent per task, review between).

To resume:
1. Read `docs/PROGRESS.md` and run `git log --oneline` to see the last completed task.
2. Open the plan; the first task with unchecked `- [ ]` steps is the next one.
3. Implement that task's steps in order (failing test → code → passing test → commit).
4. After the task: check off its `- [x]` boxes in the plan, update `docs/PROGRESS.md`,
   and commit (those two doc updates can ride in the task's commit or a follow-up).

## Conventions
- TDD: write the failing test first; never skip the "run it, watch it fail" step.
- One commit per task. End commit messages with the Co-Authored-By trailer.
- Tests mock Ollama; a running model is only needed for the final manual smoke test.
- Never modify the user's separate Obsidian vault at `F:\____IL_AI\VectorDB`.

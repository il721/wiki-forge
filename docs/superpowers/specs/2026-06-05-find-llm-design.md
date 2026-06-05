# Find LLM — Design Spec

**Date:** 2026-06-05
**Status:** Approved (design), pending implementation
**Area:** `plugins/core/llm_settings.py`, new `cockpit/llm_scan.py`

## Goal

Add a **"Find LLM"** button to the LLM Settings tab. Clicking it runs a full
local-machine scan that discovers every LLM available from this computer —
local runtimes/models *and* cloud model variants — shows a human-readable
report, and populates the model dropdown so any discovered model can be chosen.
The existing **"Compile model"** dropdown is relabeled **"Working LLM"**.

## Decisions (from brainstorming)

- **List all, all selectable** — one flat dropdown, no usable/unusable
  distinction. (Caveat below.)
- **Reimplement the scan in Python** — new `cockpit/llm_scan.py`, no PowerShell
  dependency, unit-testable.
- **Show the report** — a read-only text area in the LLM Settings tab.

### Known caveat (intentional, not a bug)

The compile/chat pipeline currently talks **only to Ollama** (`ctx.llm` is an
Ollama HTTP client). Cloud and non-Ollama entries can be *listed and selected*
in the dropdown, but the app cannot actually drive them yet. This is accepted
for now; wiring cloud providers into the pipeline is out of scope for this
feature.

## Component 1 — `cockpit/llm_scan.py`

A standalone scanner that mirrors the "pure logic + injected runners" pattern
used by `run_gate_steps` in `dashboard.py`. All real I/O (subprocess,
filesystem, environment) is injected so tests use fakes.

### Pure helpers (no I/O, unit-tested directly)

- `parse_ollama_list(text: str) -> list[str]`
  Extract model names (first column) from `ollama list` output. Skip the header
  row (`NAME  ID  SIZE  MODIFIED`), blank lines, and Ollama server log lines
  (those matching `^\s*time=`).

- `CLOUD_CATALOG: dict[str, list[str]]`
  Maps a provider key to its known model variants. Initial contents:
  - `"anthropic"` → `["claude-opus", "claude-sonnet", "claude-haiku"]`
  - `"openai"`    → `["gpt-4o", "gpt-4o-mini"]`
  - `"google"`    → `["gemini-2.0-flash", "gemini-1.5-pro"]`
  - `"mistral"`   → `["mistral-large", "mistral-small"]`
  - `"groq"`      → `["llama-3.3-70b"]`

- `detect_cloud_providers(env: Mapping, which) -> list[str]`
  Returns provider keys present in `CLOUD_CATALOG` order, detected via:
  - env var API keys: `ANTHROPIC_API_KEY`/`ANTHROPIC_AUTH_TOKEN` → `anthropic`,
    `OPENAI_API_KEY` → `openai`, `GEMINI_API_KEY`/`GOOGLE_API_KEY` → `google`,
    `MISTRAL_API_KEY` → `mistral`, `GROQ_API_KEY` → `groq`.
  - CLI presence: `which("claude")` truthy → `anthropic` (covers Claude Code
    OAuth, where no env key is set).
  Deduplicated, preserving `CLOUD_CATALOG` order.

- `expand_cloud_models(providers: Iterable[str]) -> list[str]`
  Flatten the catalog entries for the given providers, in order.

- `collect_models(sections: ScanSections) -> list[str]`
  Combine model names from all sources (Ollama, runtime model folders, loose
  weight-file stems, cloud variants), **dedupe preserving first-seen order**,
  with locals before cloud.

- `build_report(sections: ScanSections) -> str`
  Render the `=== SECTION ===` text report. Sections: `OLLAMA`,
  `OTHER LOCAL RUNTIMES`, `MODEL WEIGHT FILES`, `LLM CLI TOOLS`,
  `CLOUD PROVIDERS`. Each section lists its findings or an explicit
  "none found" line, so an empty machine still produces a coherent report.

### Orchestrator (impure, dependency-injected)

```python
def scan_local_llms(*, env=os.environ, which=shutil.which,
                    run=subprocess.run, home=Path.home) -> tuple[str, list[str]]:
    """Return (report_text, model_names). All I/O is via injected callables."""
```

Probes, then assembles `ScanSections`, then returns
`(build_report(sections), collect_models(sections))`:

1. **Ollama** — if `which("ollama")`: `run(["ollama", "list"])`, capture stdout,
   `parse_ollama_list`. On non-zero/exception: record "unreachable", no models.
2. **Other runtimes** — check known dirs under `home()`:
   `.lmstudio/models`, `.cache/lm-studio/models`, `.cache/gpt4all`,
   `.jan/models`. For each that exists, list immediate entries as runtime model
   names.
3. **Weight files** — walk under `home()` for `*.gguf` / `*.safetensors`
   (bounded, errors swallowed); report path + size; model name = file stem.
4. **CLI tools** — `which(x)` for `ollama, claude, llm, aichat`; report found
   paths (informational; not added to the dropdown).
5. **Cloud providers** — `detect_cloud_providers(env, which)` →
   `expand_cloud_models(...)`; report each provider + its variants.

The orchestrator must never raise from an individual probe failure — each
section degrades to a "none / unreachable" line so the scan as a whole always
returns a result.

## Component 2 — UI wiring (`plugins/core/llm_settings.py`)

Additive changes to the existing `QFormLayout`:

- **Relabel** the model row: `"Compile model"` → `"Working LLM"`. The settings
  key (`compile_model`) and the `self.models` widget are unchanged, so saved
  settings and the compile pipeline are unaffected.
- **New "Find LLM" button** + a `self.scan_status` `QLabel`, added as a form row
  directly under the existing "Check / refresh models" row.
- **New `self.report`** (`QPlainTextEdit(readOnly=True)`) added as a full-width
  row below the form fields so it can grow.
- **Handler `_find_llms`:** set status "Scanning…", then
  `ctx.run_job(scan_local_llms, on_done=self._show_scan, on_error=self._scan_failed)`
  so the scan runs off the UI thread.
- **`_show_scan(result)`:** unpack `(report, models)`; set the report text;
  **merge** `models` into the dropdown (add only names not already present,
  preserving the current selection — never clear it, so results from
  "Check / refresh models" or a manually typed name survive); set status to
  `Found N model(s)`.
- **`_scan_failed(msg)`:** show the error in `scan_status` and `ctx.log(msg)`.

No change to `_save`: it still persists `compile_model` from `self.models`.

## Error handling

- Per-probe failures inside `scan_local_llms` are caught and rendered as
  "none / unreachable" lines; the scan always returns a `(report, models)`
  tuple.
- A catastrophic failure of the whole job surfaces via `on_error` →
  `_scan_failed`, which updates the status label and logs — the UI never hangs.
- The dropdown merge is purely additive and dedup-guarded, so repeated scans
  never duplicate entries or lose the user's current choice.

## Testing plan (TDD)

New `tests/test_llm_scan.py`, exercising pure logic with no real I/O:

- `parse_ollama_list`: parses real-looking output, skips header/blank/`time=`
  log lines; empty input → `[]`.
- `detect_cloud_providers`: anthropic via env key; anthropic via `which("claude")`
  when no env key; openai/google/etc. via their env keys; dedupe + order.
- `expand_cloud_models`: providers → expected flattened variants, in order.
- `collect_models`: dedupe preserving order; locals before cloud.
- `build_report`: includes every section header; empty sections produce
  "none found" lines.
- `scan_local_llms` with injected fakes (`env` dict, `which` stub, `run` stub,
  `home` → `tmp_path`): returns a report containing each section and a model
  list combining the fake Ollama models + cloud variants; an exploding `run`
  for Ollama degrades gracefully instead of raising.

UI logic stays thin and is covered by the existing app smoke test
(`tests/test_app_smoke.py`) loading the plugin without error. Following project
convention, one commit per task, failing test first.

## Out of scope

- Wiring cloud/non-Ollama providers into the actual compile/chat pipeline.
- Windows-registry installed-app enumeration (the original PowerShell probe did
  this; not needed to select a "Working LLM").
- Persisting or caching scan results between sessions.

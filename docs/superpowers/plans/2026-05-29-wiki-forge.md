# Wiki-Forge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build **Wiki-Forge**, a PySide6 desktop cockpit that orchestrates the existing LLM Wiki tooling (`wiki_tool.py`), drives a local Ollama model to compile sources, manages multiple vaults, and is extensible via small plugin files.

**Architecture:** A thin Qt shell provides services (VaultManager, JobRunner, WikiToolService, LLMProvider) and UI mounting points. Every feature — Dashboard, Ingest, LLM Settings — is a plugin loaded by a PluginHost through a single `PluginContext` API. Slow work (subprocess, LLM, file scans) runs off-thread via the JobRunner. Each vault's own `scripts/wiki_tool.py` is invoked as a subprocess, leaving the deterministic tooling untouched.

**Tech Stack:** Python 3.10+, PySide6 (Qt), `requests` (Ollama HTTP), stdlib `subprocess`/`zipfile`/`json`. Tests: `pytest` + `pytest-qt`.

**Spec:** `docs/superpowers/specs/2026-05-29-wiki-forge-design.md`

---

## File Structure

```
wiki-forge/
  pyproject.toml                 # deps + pytest config
  README.md
  cockpit/
    __init__.py
    config.py                    # config_dir(), JsonStore
    vault.py                     # Vault, VaultManager (plain-Python observer)
    jobs.py                      # JobRunner, Worker (Qt threadpool)
    wiki_tool_service.py         # subprocess wrapper for wiki_tool.py + scripts
    llm/
      __init__.py
      base.py                    # LLMProvider ABC
      ollama.py                  # OllamaProvider
    plugin.py                    # Plugin base, PluginContext, _WikiToolBinding
    plugin_host.py               # discovery, load, failure isolation
    backup.py                    # backup_settings / restore_settings
    app.py                       # MainWindow, _UiHost, main()
  plugins/
    core/
      dashboard.py               # core.dashboard
      ingest.py                  # core.ingest
      llm_settings.py            # core.llm
  tests/
    conftest.py                  # vault fixture
    test_config.py
    test_vault.py
    test_jobs.py
    test_wiki_tool_service.py
    test_ollama.py
    test_plugin_host.py
    test_backup.py
    test_app_smoke.py
```

**Responsibilities (one per file):**
- `config.py` — where settings live on disk + generic JSON load/save.
- `vault.py` — vault identity, validation, registry, active-vault notifications.
- `jobs.py` — run callables off the UI thread and signal results back.
- `wiki_tool_service.py` — turn vault + command into a subprocess and capture output.
- `llm/base.py` + `llm/ollama.py` — provider contract + Ollama implementation.
- `plugin.py` — the public plugin contract and the `context` object.
- `plugin_host.py` — find/load plugins safely.
- `backup.py` — zip/unzip the config dir.
- `app.py` — wire everything into a window and mount plugins.
- `plugins/core/*` — the three built-in features, each a reference plugin.

---

## Task 1: Project scaffold + passing test harness

**Files:**
- Create: `wiki-forge/pyproject.toml`
- Create: `wiki-forge/cockpit/__init__.py`
- Create: `wiki-forge/cockpit/llm/__init__.py`
- Create: `wiki-forge/tests/__init__.py`
- Create: `wiki-forge/tests/test_smoke.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "wiki-forge"
version = "0.1.0"
description = "Desktop cockpit for managing LLM Wiki vaults"
requires-python = ">=3.10"
dependencies = [
    "PySide6>=6.6",
    "requests>=2.31",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-qt>=4.4"]

[project.scripts]
wiki-forge = "cockpit.app:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
qt_api = "pyside6"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

- [ ] **Step 2: Create empty package markers**

`cockpit/__init__.py`:
```python
"""Wiki-Forge cockpit package."""
```
`cockpit/llm/__init__.py`:
```python
"""LLM providers."""
```
`tests/__init__.py`:
```python
```

- [ ] **Step 3: Write a trivial passing test**

`tests/test_smoke.py`:
```python
def test_imports():
    import cockpit
    assert cockpit is not None
```

- [ ] **Step 4: Install deps and run the test**

Run (from `wiki-forge/`):
```bash
pip install -e ".[dev]"
pytest tests/test_smoke.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add wiki-forge/
git commit -m "chore: scaffold wiki-forge project with pytest harness"
```

---

## Task 2: Config persistence (`config.py`)

**Files:**
- Create: `wiki-forge/cockpit/config.py`
- Test: `wiki-forge/tests/test_config.py`

- [ ] **Step 1: Write the failing test**

`tests/test_config.py`:
```python
from cockpit.config import JsonStore


def test_jsonstore_saves_and_loads(tmp_path):
    path = tmp_path / "settings.json"
    store = JsonStore(path)
    assert store.data == {}            # missing file -> empty
    store.data = {"x": 1, "nested": {"a": "b"}}
    store.save()

    reloaded = JsonStore(path)
    assert reloaded.data == {"x": 1, "nested": {"a": "b"}}


def test_jsonstore_creates_parent_dirs(tmp_path):
    path = tmp_path / "deep" / "settings.json"
    store = JsonStore(path)
    store.data = {"ok": True}
    store.save()
    assert path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cockpit.config'`.

- [ ] **Step 3: Implement `config.py`**

```python
"""Where Wiki-Forge keeps its settings, and a small JSON file store."""
import json
from pathlib import Path


def config_dir() -> Path:
    """Return ~/.wiki-forge, creating it if needed."""
    d = Path.home() / ".wiki-forge"
    d.mkdir(parents=True, exist_ok=True)
    return d


class JsonStore:
    """A dict persisted to a JSON file. `.data` is the live dict."""

    def __init__(self, path):
        self.path = Path(path)
        self.data = {}
        self.load()

    def load(self) -> dict:
        if self.path.exists():
            self.data = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self.data = {}
        return self.data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add wiki-forge/cockpit/config.py wiki-forge/tests/test_config.py
git commit -m "feat: add config_dir and JsonStore persistence"
```

---

## Task 3: Vault model + VaultManager (`vault.py`)

**Files:**
- Create: `wiki-forge/cockpit/vault.py`
- Create: `wiki-forge/tests/conftest.py`
- Test: `wiki-forge/tests/test_vault.py`

- [ ] **Step 1: Create the shared `vault` fixture**

`tests/conftest.py`:
```python
import pytest


@pytest.fixture
def vault(tmp_path):
    """A minimal valid LLM Wiki vault with a stub wiki_tool.py."""
    from cockpit.vault import Vault
    root = tmp_path / "myvault"
    (root / "Raw" / "Sources").mkdir(parents=True)
    for sub in ("Topics", "Concepts", "Entities", "Projects", "Logs"):
        (root / "Wiki" / sub).mkdir(parents=True)
    (root / "scripts").mkdir(parents=True)
    # Stub tool: echoes its args so the subprocess wrapper is testable.
    (root / "scripts" / "wiki_tool.py").write_text(
        "import sys\nprint('STUB ' + ' '.join(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    return Vault(name="myvault", root=root)
```

- [ ] **Step 2: Write the failing test**

`tests/test_vault.py`:
```python
from pathlib import Path
from cockpit.config import JsonStore
from cockpit.vault import Vault, VaultManager


def test_vault_paths_and_validation(vault):
    assert vault.raw_sources.is_dir()
    assert vault.wiki.is_dir()
    assert vault.script.is_file()
    assert vault.is_valid()


def test_vault_invalid_when_missing_script(tmp_path):
    (tmp_path / "Raw").mkdir()
    (tmp_path / "Wiki").mkdir()
    assert not Vault(name="x", root=tmp_path).is_valid()


def test_manager_add_persist_reload(vault, tmp_path):
    store = JsonStore(tmp_path / "vaults.json")
    mgr = VaultManager(store)
    added = mgr.add(vault.root)
    assert added.name == "myvault"
    assert mgr.active.root == vault.root          # first vault becomes active

    mgr2 = VaultManager(JsonStore(tmp_path / "vaults.json"))
    assert [v.root for v in mgr2.vaults] == [vault.root]
    assert mgr2.active.root == vault.root


def test_manager_add_rejects_invalid(tmp_path):
    store = JsonStore(tmp_path / "vaults.json")
    mgr = VaultManager(store)
    bad = tmp_path / "not-a-vault"
    bad.mkdir()
    try:
        mgr.add(bad)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_set_active_notifies_subscribers(vault, tmp_path):
    store = JsonStore(tmp_path / "vaults.json")
    mgr = VaultManager(store)
    v = mgr.add(vault.root)
    seen = []
    mgr.subscribe(seen.append)
    mgr.set_active(v)
    assert seen == [v]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_vault.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cockpit.vault'`.

- [ ] **Step 4: Implement `vault.py`**

```python
"""Vault identity, validation, and the registry of known vaults."""
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Vault:
    name: str
    root: Path

    def __post_init__(self):
        self.root = Path(self.root)

    @property
    def raw_sources(self) -> Path:
        return self.root / "Raw" / "Sources"

    @property
    def wiki(self) -> Path:
        return self.root / "Wiki"

    @property
    def script(self) -> Path:
        return self.root / "scripts" / "wiki_tool.py"

    def is_valid(self) -> bool:
        return (self.root / "Raw").is_dir() and self.wiki.is_dir() and self.script.is_file()


class VaultManager:
    """Registry of vaults persisted via a JsonStore. Plain-Python observer."""

    def __init__(self, store):
        self.store = store
        self._vaults: list[Vault] = []
        self._active: Vault | None = None
        self._subs: list = []
        self._load()

    def _load(self):
        for v in self.store.data.get("vaults", []):
            self._vaults.append(Vault(name=v["name"], root=Path(v["root"])))
        last = self.store.data.get("active")
        if last:
            self._active = next((v for v in self._vaults if str(v.root) == last), None)
        if self._active is None and self._vaults:
            self._active = self._vaults[0]

    def _persist(self):
        self.store.data = {
            "vaults": [{"name": v.name, "root": str(v.root)} for v in self._vaults],
            "active": str(self._active.root) if self._active else None,
        }
        self.store.save()

    @property
    def vaults(self) -> list[Vault]:
        return list(self._vaults)

    @property
    def active(self) -> Vault | None:
        return self._active

    def add(self, root, name=None) -> Vault:
        vault = Vault(name=name or Path(root).name, root=Path(root))
        if not vault.is_valid():
            raise ValueError(f"Not a valid LLM Wiki vault: {root}")
        self._vaults.append(vault)
        if self._active is None:
            self._active = vault
        self._persist()
        return vault

    def remove(self, vault):
        self._vaults = [v for v in self._vaults if v.root != vault.root]
        if self._active and self._active.root == vault.root:
            self._active = self._vaults[0] if self._vaults else None
        self._persist()

    def set_active(self, vault):
        self._active = vault
        self._persist()
        for cb in self._subs:
            cb(self._active)

    def subscribe(self, cb):
        self._subs.append(cb)
```

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/test_vault.py -v`
Expected: 5 passed.
```bash
git add wiki-forge/cockpit/vault.py wiki-forge/tests/conftest.py wiki-forge/tests/test_vault.py
git commit -m "feat: add Vault model and VaultManager registry"
```

---

## Task 4: JobRunner (`jobs.py`)

**Files:**
- Create: `wiki-forge/cockpit/jobs.py`
- Test: `wiki-forge/tests/test_jobs.py`

- [x] **Step 1: Write the failing test**

`tests/test_jobs.py`:
```python
import threading
from cockpit.jobs import JobRunner


def test_job_runs_and_returns_result(qtbot):
    runner = JobRunner()
    results = []
    runner.submit(lambda: 2 + 2, on_done=results.append)
    qtbot.waitUntil(lambda: results == [4], timeout=2000)


def test_job_runs_off_main_thread(qtbot):
    runner = JobRunner()
    main_id = threading.get_ident()
    seen = []
    runner.submit(threading.get_ident, on_done=seen.append)
    qtbot.waitUntil(lambda: len(seen) == 1, timeout=2000)
    assert seen[0] != main_id


def test_job_error_goes_to_on_error(qtbot):
    runner = JobRunner()
    errors = []

    def boom():
        raise RuntimeError("nope")

    runner.submit(boom, on_error=errors.append)
    qtbot.waitUntil(lambda: errors and "nope" in errors[0], timeout=2000)
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_jobs.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cockpit.jobs'`.

- [x] **Step 3: Implement `jobs.py`**

```python
"""Run callables off the UI thread and deliver results back via signals."""
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class _WorkerSignals(QObject):
    done = Signal(object)
    error = Signal(str)


class _Worker(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
        self.signals = _WorkerSignals()

    @Slot()
    def run(self):
        try:
            result = self.fn()
        except Exception as exc:  # noqa: BLE001 - report all failures to caller
            self.signals.error.emit(str(exc))
        else:
            self.signals.done.emit(result)


class JobRunner:
    """Submit a no-arg callable; on_done/on_error fire on the UI thread."""

    def __init__(self):
        self.pool = QThreadPool.globalInstance()

    def submit(self, fn, on_done=None, on_error=None):
        worker = _Worker(fn)
        if on_done is not None:
            worker.signals.done.connect(on_done)
        if on_error is not None:
            worker.signals.error.connect(on_error)
        self.pool.start(worker)
        return worker
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_jobs.py -v`
Expected: 3 passed.

- [x] **Step 5: Commit**

```bash
git add wiki-forge/cockpit/jobs.py wiki-forge/tests/test_jobs.py
git commit -m "feat: add JobRunner for off-thread work"
```

---

## Task 5: WikiToolService (`wiki_tool_service.py`)

**Files:**
- Create: `wiki-forge/cockpit/wiki_tool_service.py`
- Test: `wiki-forge/tests/test_wiki_tool_service.py`

- [x] **Step 1: Write the failing test**

`tests/test_wiki_tool_service.py`:
```python
from cockpit.jobs import JobRunner
from cockpit.wiki_tool_service import WikiToolService


def test_run_sync_invokes_vault_script(vault):
    svc = WikiToolService(JobRunner())
    code, text = svc.run_sync(vault, ["lint"])
    assert code == 0
    assert "STUB lint" in text


def test_run_sync_passes_multiple_args(vault):
    svc = WikiToolService(JobRunner())
    code, text = svc.run_sync(vault, ["source-scan", "--update"])
    assert "STUB source-scan --update" in text


def test_run_script_sync_runs_arbitrary_script(vault):
    (vault.root / "scripts" / "audit_public.py").write_text(
        "print('AUDIT OK')\n", encoding="utf-8")
    svc = WikiToolService(JobRunner())
    code, text = svc.run_script_sync(vault, "scripts/audit_public.py")
    assert code == 0
    assert "AUDIT OK" in text


def test_run_async_delivers_text(vault, qtbot):
    svc = WikiToolService(JobRunner())
    out = []
    svc.run(vault, ["doctor"], on_done=out.append)
    qtbot.waitUntil(lambda: out and "STUB doctor" in out[0], timeout=2000)
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_wiki_tool_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cockpit.wiki_tool_service'`.

- [x] **Step 3: Implement `wiki_tool_service.py`**

```python
"""Invoke a vault's own scripts as subprocesses and capture their output."""
import subprocess
import sys


class WikiToolService:
    def __init__(self, job_runner):
        self.jobs = job_runner

    def run_sync(self, vault, args):
        """Run `python <vault>/scripts/wiki_tool.py <args>`; return (code, text)."""
        cmd = [sys.executable, str(vault.script), *args]
        proc = subprocess.run(
            cmd, cwd=str(vault.root), capture_output=True, text=True
        )
        return proc.returncode, proc.stdout + proc.stderr

    def run_script_sync(self, vault, rel_script, args=()):
        """Run any script relative to the vault root; return (code, text)."""
        cmd = [sys.executable, str(vault.root / rel_script), *args]
        proc = subprocess.run(
            cmd, cwd=str(vault.root), capture_output=True, text=True
        )
        return proc.returncode, proc.stdout + proc.stderr

    def run(self, vault, args, on_done=None, on_error=None):
        """Async variant: delivers combined output text to on_done."""
        def work():
            _code, text = self.run_sync(vault, args)
            return text
        self.jobs.submit(work, on_done=on_done, on_error=on_error)
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_wiki_tool_service.py -v`
Expected: 4 passed.

- [x] **Step 5: Commit**

```bash
git add wiki-forge/cockpit/wiki_tool_service.py wiki-forge/tests/test_wiki_tool_service.py
git commit -m "feat: add WikiToolService subprocess wrapper"
```

---

## Task 6: LLM provider — base + Ollama (`llm/base.py`, `llm/ollama.py`)

**Files:**
- Create: `wiki-forge/cockpit/llm/base.py`
- Create: `wiki-forge/cockpit/llm/ollama.py`
- Test: `wiki-forge/tests/test_ollama.py`

- [x] **Step 1: Write the failing test**

`tests/test_ollama.py`:
```python
from cockpit.llm.ollama import OllamaProvider


class _FakeResp:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


def test_health_true_when_tags_ok(monkeypatch):
    monkeypatch.setattr(
        "cockpit.llm.ollama.requests.get", lambda *a, **k: _FakeResp(200))
    assert OllamaProvider().health() is True


def test_health_false_on_exception(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.RequestException("down")

    monkeypatch.setattr("cockpit.llm.ollama.requests.get", boom)
    assert OllamaProvider().health() is False


def test_list_models_parses_names(monkeypatch):
    payload = {"models": [{"name": "llama3"}, {"name": "qwen2"}]}
    monkeypatch.setattr(
        "cockpit.llm.ollama.requests.get", lambda *a, **k: _FakeResp(200, payload))
    assert OllamaProvider().list_models() == ["llama3", "qwen2"]


def test_generate_returns_response_field(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResp(200, {"response": "hello world"})

    monkeypatch.setattr("cockpit.llm.ollama.requests.post", fake_post)
    out = OllamaProvider().generate("hi", model="llama3")
    assert out == "hello world"
    assert captured["json"]["model"] == "llama3"
    assert captured["json"]["stream"] is False
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ollama.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cockpit.llm.ollama'`.

- [x] **Step 3: Implement `llm/base.py`**

```python
"""The provider contract every LLM backend implements."""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def health(self) -> bool:
        """True if the backend is reachable."""

    @abstractmethod
    def list_models(self) -> list[str]:
        """Available model names."""

    @abstractmethod
    def generate(self, prompt: str, model: str | None = None, **opts) -> str:
        """Return the model's completion for prompt."""
```

- [x] **Step 4: Implement `llm/ollama.py`**

```python
"""Ollama implementation of LLMProvider (http://localhost:11434)."""
import requests

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url="http://localhost:11434", timeout=120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        r = requests.get(f"{self.base_url}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]

    def generate(self, prompt: str, model: str | None = None, **opts) -> str:
        payload = {"model": model or "llama3", "prompt": prompt, "stream": False}
        payload.update(opts)
        r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("response", "")
```

- [x] **Step 5: Run tests and commit**

Run: `pytest tests/test_ollama.py -v`
Expected: 4 passed.
```bash
git add wiki-forge/cockpit/llm/base.py wiki-forge/cockpit/llm/ollama.py wiki-forge/tests/test_ollama.py
git commit -m "feat: add LLMProvider contract and OllamaProvider"
```

---

## Task 7: Plugin contract — base + context (`plugin.py`)

**Files:**
- Create: `wiki-forge/cockpit/plugin.py`
- Test: covered by Task 8 (plugin host). This task adds a focused context test below.
- Test: `wiki-forge/tests/test_plugin_context.py`

- [x] **Step 1: Write the failing test**

`tests/test_plugin_context.py`:
```python
from cockpit.config import JsonStore
from cockpit.jobs import JobRunner
from cockpit.vault import VaultManager
from cockpit.wiki_tool_service import WikiToolService
from cockpit.plugin import Plugin, PluginContext


class _FakeUi:
    def __init__(self):
        self.tabs = []
    def add_tab(self, plugin, widget):
        self.tabs.append((plugin.id, widget))
    def add_toolbar_action(self, plugin, label, fn):
        pass
    def add_dashboard_card(self, plugin, widget):
        pass


def _make_ctx(vault, tmp_path):
    vm = VaultManager(JsonStore(tmp_path / "vaults.json"))
    vm.add(vault.root)
    svc = WikiToolService(JobRunner())
    plugin = Plugin()
    plugin.id = "test.plugin"
    ui = _FakeUi()
    ctx = PluginContext(
        plugin=plugin, vault_manager=vm, job_runner=JobRunner(),
        wiki_tool=svc, llm=None, settings={}, log=lambda m: None, ui=ui,
    )
    return ctx, ui, vm


def test_context_exposes_active_vault(vault, tmp_path):
    ctx, _ui, vm = _make_ctx(vault, tmp_path)
    assert ctx.active_vault.root == vm.active.root


def test_context_on_vault_changed_fires(vault, tmp_path):
    ctx, _ui, vm = _make_ctx(vault, tmp_path)
    seen = []
    ctx.on_vault_changed(seen.append)
    vm.set_active(vm.active)
    assert len(seen) == 1


def test_wiki_tool_binding_uses_active_vault(vault, tmp_path, qtbot):
    ctx, _ui, _vm = _make_ctx(vault, tmp_path)
    code, text = ctx.wiki_tool.run_sync("lint")
    assert code == 0 and "STUB lint" in text


def test_add_tab_reaches_ui(vault, tmp_path):
    ctx, ui, _vm = _make_ctx(vault, tmp_path)
    sentinel = object()
    ctx.add_tab(sentinel)
    assert ui.tabs == [("test.plugin", sentinel)]
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_plugin_context.py -v`
Expected: FAIL with `ImportError` (no `PluginContext` in `cockpit.plugin`).

- [x] **Step 3: Implement `plugin.py`**

```python
"""The public plugin contract: the base class and the context object.

Plugins depend ONLY on PluginContext. They never import the shell or each other.
"""


class Plugin:
    id = "unknown.plugin"
    name = "Unnamed"
    version = "0.0.0"

    def activate(self, ctx: "PluginContext") -> None:
        """Build UI and mount it via ctx. Called once at load."""

    def deactivate(self) -> None:
        """Optional cleanup (timers, threads)."""


class _WikiToolBinding:
    """Binds WikiToolService to whatever vault is currently active."""

    def __init__(self, service, active_provider):
        self._svc = service
        self._active = active_provider  # callable -> Vault

    def run(self, *args, on_done=None, on_error=None):
        self._svc.run(self._active(), list(args), on_done=on_done, on_error=on_error)

    def run_sync(self, *args):
        return self._svc.run_sync(self._active(), list(args))

    def run_script_sync(self, rel_script, *args):
        return self._svc.run_script_sync(self._active(), rel_script, list(args))


class PluginContext:
    """A plugin's entire API surface to the app."""

    def __init__(self, *, plugin, vault_manager, job_runner, wiki_tool,
                 llm, settings, log, ui):
        self.plugin = plugin
        self._vm = vault_manager
        self._jobs = job_runner
        self._llm = llm
        self._log = log
        self._ui = ui
        self.settings = settings  # per-plugin dict, persisted by the shell
        self.wiki_tool = _WikiToolBinding(wiki_tool, lambda: vault_manager.active)

    @property
    def active_vault(self):
        return self._vm.active

    def on_vault_changed(self, cb):
        self._vm.subscribe(cb)

    @property
    def llm(self):
        return self._llm

    def run_job(self, fn, on_done=None, on_error=None):
        self._jobs.submit(fn, on_done=on_done, on_error=on_error)

    def add_tab(self, widget):
        self._ui.add_tab(self.plugin, widget)

    def add_toolbar_action(self, label, fn):
        self._ui.add_toolbar_action(self.plugin, label, fn)

    def add_dashboard_card(self, widget):
        self._ui.add_dashboard_card(self.plugin, widget)

    def log(self, msg):
        self._log(msg)
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_plugin_context.py -v`
Expected: 4 passed.

- [x] **Step 5: Commit**

```bash
git add wiki-forge/cockpit/plugin.py wiki-forge/tests/test_plugin_context.py
git commit -m "feat: add Plugin base class and PluginContext API"
```

---

## Task 8: PluginHost — discovery + failure isolation (`plugin_host.py`)

**Files:**
- Create: `wiki-forge/cockpit/plugin_host.py`
- Test: `wiki-forge/tests/test_plugin_host.py`

- [x] **Step 1: Write the failing test**

`tests/test_plugin_host.py`:
```python
from cockpit.plugin_host import PluginHost


def _write(dirpath, name, body):
    (dirpath / name).write_text(body, encoding="utf-8")


def test_loads_good_skips_bad(tmp_path):
    pdir = tmp_path / "plugins"
    pdir.mkdir()
    _write(pdir, "good_plugin.py",
           "from cockpit.plugin import Plugin\n"
           "class Good(Plugin):\n"
           "    id = 'x.good'\n"
           "    def activate(self, ctx):\n"
           "        ctx.log('activated')\n")
    _write(pdir, "bad_plugin.py",
           "from cockpit.plugin import Plugin\n"
           "class Bad(Plugin):\n"
           "    id = 'x.bad'\n"
           "    def activate(self, ctx):\n"
           "        raise RuntimeError('explode')\n")

    logs = []

    class FakeCtx:
        def log(self, m): logs.append(m)

    host = PluginHost([pdir], context_factory=lambda plugin: FakeCtx())
    host.load_all()

    loaded_ids = [p.id for p, _ in host.loaded]
    failed_names = [name for name, _err in host.failed]
    assert "x.good" in loaded_ids
    assert "Bad" in failed_names
    assert "activated" in logs


def test_ignores_underscore_files(tmp_path):
    pdir = tmp_path / "plugins"
    pdir.mkdir()
    _write(pdir, "_helper.py", "raise RuntimeError('should not import')\n")
    host = PluginHost([pdir], context_factory=lambda plugin: None)
    host.load_all()
    assert host.failed == []
    assert host.loaded == []
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_plugin_host.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cockpit.plugin_host'`.

- [x] **Step 3: Implement `plugin_host.py`**

```python
"""Discover plugin files, instantiate them, and isolate failures."""
import importlib.util
import inspect
import traceback
from pathlib import Path

from cockpit.plugin import Plugin


class PluginHost:
    def __init__(self, plugin_dirs, context_factory, log=print):
        self.plugin_dirs = [Path(d) for d in plugin_dirs]
        self.context_factory = context_factory
        self.log = log
        self.loaded = []   # list[(plugin_instance, context)]
        self.failed = []   # list[(name, traceback_str)]

    def _classes_in(self, path):
        spec = importlib.util.spec_from_file_location(f"wf_plugin_{path.stem}", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        found = []
        for _name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, Plugin) and obj is not Plugin and obj.__module__ == mod.__name__:
                found.append(obj)
        return found

    def discover(self):
        classes = []
        for d in self.plugin_dirs:
            if not d.exists():
                continue
            for f in sorted(d.rglob("*.py")):
                if f.name.startswith("_"):
                    continue
                try:
                    classes.extend(self._classes_in(f))
                except Exception:
                    self.failed.append((str(f), traceback.format_exc()))
        return classes

    def load_all(self):
        for cls in self.discover():
            try:
                inst = cls()
                ctx = self.context_factory(inst)
                inst.activate(ctx)
                self.loaded.append((inst, ctx))
            except Exception:
                self.failed.append((cls.__name__, traceback.format_exc()))
                self.log(f"[plugin-host] failed to load {cls.__name__}")
        return self.loaded
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_plugin_host.py -v`
Expected: 2 passed.

- [x] **Step 5: Commit**

```bash
git add wiki-forge/cockpit/plugin_host.py wiki-forge/tests/test_plugin_host.py
git commit -m "feat: add PluginHost with discovery and failure isolation"
```

---

## Task 9: Backup / restore settings (`backup.py`)

**Files:**
- Create: `wiki-forge/cockpit/backup.py`
- Test: `wiki-forge/tests/test_backup.py`

- [x] **Step 1: Write the failing test**

`tests/test_backup.py`:
```python
import json
from cockpit.backup import backup_settings, restore_settings


def test_backup_then_restore_roundtrip(tmp_path):
    cfg = tmp_path / "cfg"
    (cfg / "plugins").mkdir(parents=True)
    (cfg / "vaults.json").write_text(json.dumps({"vaults": []}), encoding="utf-8")
    (cfg / "settings.json").write_text(json.dumps({"x": 1}), encoding="utf-8")
    (cfg / "plugins" / "extra.py").write_text("# plugin\n", encoding="utf-8")

    zip_path = tmp_path / "backup.zip"
    backup_settings(cfg, zip_path)
    assert zip_path.exists()

    target = tmp_path / "restored"
    restore_settings(zip_path, target)
    assert json.loads((target / "settings.json").read_text())["x"] == 1
    assert (target / "plugins" / "extra.py").exists()
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_backup.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cockpit.backup'`.

- [x] **Step 3: Implement `backup.py`**

```python
"""Zip the whole config dir for backup, and unzip to restore."""
import zipfile
from pathlib import Path


def backup_settings(config_dir, dest_zip) -> Path:
    config_dir = Path(config_dir)
    dest = Path(dest_zip)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(config_dir.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(config_dir).as_posix())
    return dest


def restore_settings(src_zip, config_dir) -> None:
    config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src_zip, "r") as zf:
        zf.extractall(config_dir)
```

- [x] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_backup.py -v`
Expected: 1 passed.

- [x] **Step 5: Commit**

```bash
git add wiki-forge/cockpit/backup.py wiki-forge/tests/test_backup.py
git commit -m "feat: add settings backup/restore"
```

---

## Task 10: Application shell (`app.py`)

**Files:**
- Create: `wiki-forge/cockpit/app.py`
- Test: `wiki-forge/tests/test_app_smoke.py`

This wires services + UI host + PluginHost into a MainWindow. The `_UiHost` adapts plugin mount calls to Qt widgets. Per-plugin settings are namespaced inside `settings.json` under `plugins.<id>` and saved on close.

- [x] **Step 1: Write the failing smoke test**

`tests/test_app_smoke.py`:
```python
from cockpit.app import MainWindow


def test_mainwindow_loads_core_plugins(qtbot, tmp_path, monkeypatch):
    # Point config at a temp dir so the test never touches the real ~/.wiki-forge.
    import cockpit.app as app_mod
    monkeypatch.setattr(app_mod, "config_dir", lambda: tmp_path)

    win = MainWindow()
    qtbot.addWidget(win)
    # The three core plugins each add a tab.
    labels = [win.tabs.tabText(i) for i in range(win.tabs.count())]
    assert "Dashboard" in labels
    assert "Ingest" in labels
    assert "LLM Settings" in labels
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_app_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'cockpit.app'`.

- [x] **Step 3: Implement `app.py`**

```python
"""Wiki-Forge main window: wires services and mounts plugins."""
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QLabel, QPushButton, QTabWidget, QPlainTextEdit, QDockWidget, QFileDialog,
    QMessageBox, QToolBar,
)
from PySide6.QtCore import Qt

from cockpit.config import config_dir, JsonStore
from cockpit.vault import VaultManager
from cockpit.jobs import JobRunner
from cockpit.wiki_tool_service import WikiToolService
from cockpit.llm.ollama import OllamaProvider
from cockpit.plugin import PluginContext
from cockpit.plugin_host import PluginHost
from cockpit.backup import backup_settings, restore_settings


class _UiHost:
    """Adapts plugin mount calls to the window's Qt widgets."""

    def __init__(self, window):
        self.w = window

    def add_tab(self, plugin, widget):
        self.w.tabs.addTab(widget, plugin.name)

    def add_toolbar_action(self, plugin, label, fn):
        act = self.w.toolbar.addAction(label)
        act.triggered.connect(fn)

    def add_dashboard_card(self, plugin, widget):
        self.w.dashboard_cards.append(widget)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wiki-Forge")
        self.resize(1000, 700)
        self.dashboard_cards = []

        cfg = config_dir()
        self.vaults_store = JsonStore(cfg / "vaults.json")
        self.settings_store = JsonStore(cfg / "settings.json")
        self.settings_store.data.setdefault("plugins", {})
        self.settings_store.data.setdefault("ollama_url", "http://localhost:11434")

        self.vault_manager = VaultManager(self.vaults_store)
        self.jobs = JobRunner()
        self.wiki_tool = WikiToolService(self.jobs)
        self.llm = OllamaProvider(self.settings_store.data["ollama_url"])

        self._build_ui()
        self._build_menu()

        plugin_dirs = [
            Path(__file__).resolve().parent.parent / "plugins" / "core",
            config_dir() / "plugins",
        ]
        self.host = PluginHost(plugin_dirs, context_factory=self._make_context,
                               log=self.log)
        self.host.load_all()
        self._refresh_vault_combo()

    # --- UI construction ---------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)

        top = QHBoxLayout()
        top.addWidget(QLabel("Vault:"))
        self.vault_combo = QComboBox()
        self.vault_combo.currentIndexChanged.connect(self._on_combo_changed)
        top.addWidget(self.vault_combo, 1)
        add_btn = QPushButton("+ Add vault")
        add_btn.clicked.connect(self._add_vault)
        top.addWidget(add_btn)
        layout.addLayout(top)

        self.toolbar = QToolBar("Actions")
        self.addToolBar(self.toolbar)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        self.log_view = QPlainTextEdit(readOnly=True)
        dock = QDockWidget("Log", self)
        dock.setWidget(self.log_view)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Backup settings…", self._backup)
        file_menu.addAction("Restore settings…", self._restore)
        file_menu.addSeparator()
        file_menu.addAction("Reload plugins", self._reload_plugins)

    # --- plugin wiring -----------------------------------------------------
    def _make_context(self, plugin):
        plugins_cfg = self.settings_store.data["plugins"]
        plugins_cfg.setdefault(plugin.id, {})
        return PluginContext(
            plugin=plugin,
            vault_manager=self.vault_manager,
            job_runner=self.jobs,
            wiki_tool=self.wiki_tool,
            llm=self.llm,
            settings=plugins_cfg[plugin.id],
            log=self.log,
            ui=_UiHost(self),
        )

    # --- vault switcher ----------------------------------------------------
    def _refresh_vault_combo(self):
        self.vault_combo.blockSignals(True)
        self.vault_combo.clear()
        for v in self.vault_manager.vaults:
            self.vault_combo.addItem(v.name, v)
        active = self.vault_manager.active
        if active:
            idx = next((i for i in range(self.vault_combo.count())
                        if self.vault_combo.itemData(i).root == active.root), -1)
            if idx >= 0:
                self.vault_combo.setCurrentIndex(idx)
        self.vault_combo.blockSignals(False)
        if active:
            self.vault_manager.set_active(active)  # fire initial refresh

    def _on_combo_changed(self, idx):
        vault = self.vault_combo.itemData(idx)
        if vault is not None:
            self.vault_manager.set_active(vault)

    def _add_vault(self):
        folder = QFileDialog.getExistingDirectory(self, "Select an LLM Wiki vault folder")
        if not folder:
            return
        try:
            self.vault_manager.add(folder)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid vault", str(exc))
            return
        self._refresh_vault_combo()

    # --- menu actions ------------------------------------------------------
    def _backup(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup settings", "wiki-forge-backup.zip", "Zip (*.zip)")
        if path:
            backup_settings(config_dir(), path)
            self.log(f"Settings backed up to {path}")

    def _restore(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Restore settings", "", "Zip (*.zip)")
        if not path:
            return
        if QMessageBox.question(self, "Restore",
                                "Overwrite current settings with this backup?") \
                == QMessageBox.Yes:
            restore_settings(path, config_dir())
            QMessageBox.information(self, "Restore",
                                    "Restored. Restart Wiki-Forge to apply.")

    def _reload_plugins(self):
        QMessageBox.information(self, "Reload plugins",
                                "Restart Wiki-Forge to load plugin changes.")

    # --- shared services ---------------------------------------------------
    def log(self, msg):
        self.log_view.appendPlainText(str(msg))

    def closeEvent(self, event):
        self.settings_store.save()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

> **Note:** the smoke test patches `cockpit.app.config_dir`. Because Tasks 11–12 create the three core plugins, this test only passes once those files exist. Run it after Task 12 (it is expected to fail until then). To keep Task 10 green on its own, temporarily assert `win.tabs is not None` and tighten the assertion in Task 12 Step 4. Use this simpler test body for Step 1 now:

```python
def test_mainwindow_constructs(qtbot, tmp_path, monkeypatch):
    import cockpit.app as app_mod
    monkeypatch.setattr(app_mod, "config_dir", lambda: tmp_path)
    win = MainWindow()
    qtbot.addWidget(win)
    assert win.tabs is not None
```

- [x] **Step 4: Run the simpler smoke test**

Run: `pytest tests/test_app_smoke.py -v`
Expected: 1 passed (no core plugins yet; `tabs` exists).

- [x] **Step 5: Commit**

```bash
git add wiki-forge/cockpit/app.py wiki-forge/tests/test_app_smoke.py
git commit -m "feat: add MainWindow shell with vault switcher, plugin host, backup menu"
```

---

## Task 11: Core plugin — Dashboard + LLM Settings (`plugins/core/dashboard.py`, `plugins/core/llm_settings.py`)

**Files:**
- Create: `wiki-forge/plugins/core/dashboard.py`
- Create: `wiki-forge/plugins/core/llm_settings.py`
- Test: `wiki-forge/tests/test_dashboard_logic.py`

- [x] **Step 1: Write the failing logic test (gate sequencing helper)**

`tests/test_dashboard_logic.py`:
```python
from plugins.core.dashboard import run_gate_steps


def test_gate_stops_on_first_failure():
    calls = []

    def runner(args):
        calls.append(args)
        # 'lint' fails (returns code 1); later steps must not run.
        return (1, "lint error") if args == ["lint"] else (0, "ok")

    steps = [["doctor"], ["build"], ["lint"], ["source-lint"]]
    code, log = run_gate_steps(steps, runner)
    assert code == 1
    assert calls == [["doctor"], ["build"], ["lint"]]   # stopped after lint
    assert "FAILED" in log


def test_gate_runs_all_when_passing():
    def runner(args):
        return (0, "ok")
    steps = [["doctor"], ["build"]]
    code, log = run_gate_steps(steps, runner)
    assert code == 0
    assert "FAILED" not in log
```

- [x] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard_logic.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'plugins.core.dashboard'`.

> If import fails on `plugins` not being a package, add empty `wiki-forge/plugins/__init__.py` and `wiki-forge/plugins/core/__init__.py`. Create them now.

- [x] **Step 3: Implement `plugins/core/dashboard.py`**

```python
"""Dashboard plugin: health, counts, coverage, and the maintenance gate."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLabel

from cockpit.plugin import Plugin


def run_gate_steps(steps, runner):
    """Run (code, text) steps in order; stop at first non-zero. Pure/testable."""
    out = []
    for args in steps:
        code, text = runner(args)
        out.append(f"$ wiki_tool {' '.join(args)}\n{text}")
        if code != 0:
            out.append(f"GATE FAILED at: {' '.join(args)}")
            return code, "\n".join(out)
    return 0, "\n".join(out)


class DashboardPlugin(Plugin):
    id, name, version = "core.dashboard", "Dashboard", "1.0.0"

    GATE = [["doctor"], ["build"], ["lint"], ["source-lint"]]

    def activate(self, ctx):
        self.ctx = ctx
        w = QWidget()
        lay = QVBoxLayout(w)
        self.status = QLabel("No vault selected.")
        self.output = QPlainTextEdit(readOnly=True)
        lay.addWidget(self.status)
        lay.addWidget(self.output, 1)
        ctx.add_tab(w)

        ctx.add_toolbar_action("Doctor", lambda: self._single(["doctor"]))
        ctx.add_toolbar_action("Build", lambda: self._single(["build"]))
        ctx.add_toolbar_action("Lint", lambda: self._single(["lint"]))
        ctx.add_toolbar_action("Run maintenance gate", self._gate)

        ctx.on_vault_changed(self._on_vault)

    def _on_vault(self, vault):
        if vault is None:
            self.status.setText("No vault selected.")
        else:
            self.status.setText(f"Active vault: {vault.name}  ({vault.root})")
            self._single(["doctor"])

    def _single(self, args):
        if self.ctx.active_vault is None:
            return
        self.ctx.wiki_tool.run(*args, on_done=self.output.setPlainText)

    def _gate(self):
        if self.ctx.active_vault is None:
            return
        runner = lambda a: self.ctx.wiki_tool.run_sync(*a)
        self.ctx.run_job(
            lambda: run_gate_steps(self.GATE, runner)[1],
            on_done=self.output.setPlainText,
        )
```

- [x] **Step 4: Implement `plugins/core/llm_settings.py`**

```python
"""LLM Settings plugin: Ollama endpoint, model selection, health check."""
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QComboBox, QPushButton, QLabel, QDoubleSpinBox,
)

from cockpit.plugin import Plugin


class LlmSettingsPlugin(Plugin):
    id, name, version = "core.llm", "LLM Settings", "1.0.0"

    def activate(self, ctx):
        self.ctx = ctx
        s = ctx.settings
        s.setdefault("compile_model", "llama3")
        s.setdefault("chat_model", "llama3")
        s.setdefault("temperature", 0.2)

        w = QWidget()
        form = QFormLayout(w)

        self.url = QLineEdit(getattr(ctx.llm, "base_url", "http://localhost:11434"))
        form.addRow("Ollama URL", self.url)

        self.models = QComboBox()
        self.models.setEditable(True)
        self.models.setCurrentText(s["compile_model"])
        form.addRow("Compile model", self.models)

        self.temp = QDoubleSpinBox()
        self.temp.setRange(0.0, 2.0)
        self.temp.setSingleStep(0.1)
        self.temp.setValue(float(s["temperature"]))
        form.addRow("Temperature", self.temp)

        self.health = QLabel("Unknown")
        check = QPushButton("Check / refresh models")
        check.clicked.connect(self._check)
        form.addRow(check, self.health)

        save = QPushButton("Save")
        save.clicked.connect(self._save)
        form.addRow(save)

        ctx.add_tab(w)

    def _check(self):
        self.ctx.llm.base_url = self.url.text().rstrip("/")
        ok = self.ctx.llm.health()
        self.health.setText("Reachable" if ok else "Not reachable")
        if ok:
            self.ctx.run_job(self.ctx.llm.list_models, on_done=self._fill_models)

    def _fill_models(self, names):
        current = self.models.currentText()
        self.models.clear()
        self.models.addItems(names)
        self.models.setCurrentText(current)

    def _save(self):
        self.ctx.llm.base_url = self.url.text().rstrip("/")
        self.ctx.settings["compile_model"] = self.models.currentText()
        self.ctx.settings["temperature"] = self.temp.value()
        self.ctx.log("LLM settings saved.")
```

- [x] **Step 5: Run logic test and commit**

Run: `pytest tests/test_dashboard_logic.py -v`
Expected: 2 passed.
```bash
git add wiki-forge/plugins/__init__.py wiki-forge/plugins/core/__init__.py \
        wiki-forge/plugins/core/dashboard.py wiki-forge/plugins/core/llm_settings.py \
        wiki-forge/tests/test_dashboard_logic.py
git commit -m "feat: add Dashboard and LLM Settings core plugins"
```

---

## Task 12: Core plugin — Ingest & Compile (`plugins/core/ingest.py`)

**Files:**
- Create: `wiki-forge/plugins/core/ingest.py`
- Modify: `wiki-forge/tests/test_app_smoke.py` (tighten assertion now that all 3 plugins exist)
- Test: `wiki-forge/tests/test_ingest_logic.py`

- [ ] **Step 1: Write the failing logic test (note builder)**

`tests/test_ingest_logic.py`:
```python
from plugins.core.ingest import build_wiki_note


def test_build_wiki_note_has_frontmatter_and_source_link():
    note = build_wiki_note(
        body="A compiled concept body.",
        source_rel="Raw/Sources/example.md",
        tag="concept",
        today="2026-05-29",
    )
    assert note.startswith("---")
    assert 'tags:\n  - "concept"' in note
    assert "sources:\n  - \"Raw/Sources/example.md\"" in note
    assert "source_count: 1" in note
    assert "A compiled concept body." in note
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ingest_logic.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'plugins.core.ingest'`.

- [ ] **Step 3: Implement `plugins/core/ingest.py`**

```python
"""Ingest & Compile plugin: raw sources -> LLM-drafted Wiki notes (reviewed)."""
from datetime import date
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QPlainTextEdit, QPushButton,
    QComboBox, QLabel, QMessageBox,
)

from cockpit.plugin import Plugin

FOLDER_FOR_TAG = {
    "concept": "Concepts", "topic": "Topics", "entity": "Entities",
    "project": "Projects", "log": "Logs",
}

COMPILE_PROMPT = (
    "You are compiling a raw source into a concise, reusable wiki note. "
    "Write clear markdown body text only (no frontmatter). "
    "Every claim must be supported by the source.\n\nSOURCE:\n{source}"
)


def build_wiki_note(body, source_rel, tag, today):
    """Compose a compiled Wiki note with schema-correct frontmatter. Pure/testable."""
    fm = (
        "---\n"
        "tags:\n"
        f'  - "{tag}"\n'
        "topics: []\n"
        "status: seed\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "sources:\n"
        f'  - "{source_rel}"\n'
        "source_count: 1\n"
        "aliases: []\n"
        "---\n\n"
    )
    return fm + body.strip() + "\n"


class IngestPlugin(Plugin):
    id, name, version = "core.ingest", "Ingest", "1.0.0"

    def activate(self, ctx):
        self.ctx = ctx
        w = QWidget()
        outer = QHBoxLayout(w)

        left = QVBoxLayout()
        left.addWidget(QLabel("Raw sources"))
        self.list = QListWidget()
        self.list.currentTextChanged.connect(self._show_source)
        left.addWidget(self.list, 1)
        outer.addLayout(left, 1)

        right = QVBoxLayout()
        self.source_view = QPlainTextEdit(readOnly=True)
        right.addWidget(QLabel("Source"))
        right.addWidget(self.source_view, 1)

        controls = QHBoxLayout()
        self.tag = QComboBox()
        self.tag.addItems(list(FOLDER_FOR_TAG.keys()))
        controls.addWidget(QLabel("Compile as"))
        controls.addWidget(self.tag)
        compile_btn = QPushButton("Compile with LLM")
        compile_btn.clicked.connect(self._compile)
        controls.addWidget(compile_btn)
        right.addLayout(controls)

        self.draft = QPlainTextEdit()
        right.addWidget(QLabel("Draft (review before saving)"))
        right.addWidget(self.draft, 1)
        save_btn = QPushButton("Save to Wiki + update manifest")
        save_btn.clicked.connect(self._save)
        right.addWidget(save_btn)
        outer.addLayout(right, 2)

        ctx.add_tab(w)
        ctx.on_vault_changed(self._reload_sources)

    def _reload_sources(self, vault):
        self.list.clear()
        if vault is None:
            return
        for p in sorted(vault.raw_sources.glob("*.md")):
            self.list.addItem(p.name)

    def _current_source_path(self):
        vault = self.ctx.active_vault
        item = self.list.currentItem()
        if vault is None or item is None:
            return None
        return vault.raw_sources / item.text()

    def _show_source(self, _name):
        p = self._current_source_path()
        if p and p.exists():
            self.source_view.setPlainText(p.read_text(encoding="utf-8"))

    def _compile(self):
        p = self._current_source_path()
        if p is None:
            return
        if not self.ctx.llm.health():
            QMessageBox.warning(self.draft, "Ollama",
                                "Ollama is not reachable. Check LLM Settings.")
            return
        prompt = COMPILE_PROMPT.format(source=p.read_text(encoding="utf-8"))
        model = self.ctx.settings.get("compile_model", "llama3")
        self.draft.setPlainText("Compiling…")
        self.ctx.run_job(
            lambda: self.ctx.llm.generate(prompt, model=model),
            on_done=self.draft.setPlainText,
            on_error=lambda e: self.draft.setPlainText(f"Error: {e}"),
        )

    def _save(self):
        vault = self.ctx.active_vault
        src = self._current_source_path()
        if vault is None or src is None:
            return
        tag = self.tag.currentText()
        source_rel = src.relative_to(vault.root).as_posix()
        note = build_wiki_note(self.draft.toPlainText(), source_rel, tag,
                               date.today().isoformat())
        dest_dir = vault.wiki / FOLDER_FOR_TAG[tag]
        dest = dest_dir / src.name
        dest.write_text(note, encoding="utf-8")
        self.ctx.log(f"Wrote {dest}")
        # Refresh manifest + lint via the deterministic tooling.
        self.ctx.wiki_tool.run("source-scan", "--update", "--accept-covered",
                               on_done=self.ctx.log)
```

- [ ] **Step 4: Tighten the app smoke test**

Replace the body of `tests/test_app_smoke.py` with the full three-plugin assertion:
```python
from cockpit.app import MainWindow


def test_mainwindow_loads_core_plugins(qtbot, tmp_path, monkeypatch):
    import cockpit.app as app_mod
    monkeypatch.setattr(app_mod, "config_dir", lambda: tmp_path)
    win = MainWindow()
    qtbot.addWidget(win)
    labels = [win.tabs.tabText(i) for i in range(win.tabs.count())]
    assert "Dashboard" in labels
    assert "Ingest" in labels
    assert "LLM Settings" in labels
```

- [ ] **Step 5: Run the full suite and commit**

Run: `pytest -v`
Expected: all tests pass (config, vault, jobs, wiki_tool_service, ollama, plugin_context, plugin_host, backup, dashboard_logic, ingest_logic, app_smoke).
```bash
git add wiki-forge/plugins/core/ingest.py wiki-forge/tests/test_ingest_logic.py \
        wiki-forge/tests/test_app_smoke.py
git commit -m "feat: add Ingest & Compile core plugin; full plugin set loads"
```

---

## Task 13: README + manual smoke checklist

**Files:**
- Create: `wiki-forge/README.md`

- [ ] **Step 1: Write `README.md`**

```markdown
# Wiki-Forge

Desktop cockpit for managing Obsidian-based LLM Wiki vaults. Complements Obsidian
(your editor) with: a control panel over each vault's `wiki_tool.py`, an LLM-assisted
ingest/compile workspace, multi-vault switching, and a small plugin system.

## Install
```bash
cd wiki-forge
pip install -e ".[dev]"
```

## Run
```bash
wiki-forge        # or: python -m cockpit.app
```
Requires [Ollama](https://ollama.com) running locally for compile features.

## Writing a plugin
Drop a `.py` file in `~/.wiki-forge/plugins/` exposing a `cockpit.plugin.Plugin`
subclass. Restart Wiki-Forge. See `plugins/core/dashboard.py` for a reference.

## Tests
```bash
pytest -v
```
```

- [ ] **Step 2: Manual smoke checklist (run once with a real vault + Ollama)**

- [ ] Launch `wiki-forge`; window opens with Dashboard/Ingest/LLM Settings tabs.
- [ ] **+ Add vault** → pick the existing LLM Wiki folder (e.g. `F:\____IL_AI\VectorDB`); it appears in the dropdown.
- [ ] Dashboard shows the active vault; **Run maintenance gate** streams doctor/build/lint/source-lint output and stops on any failure.
- [ ] LLM Settings → **Check / refresh models** shows "Reachable" and lists Ollama models.
- [ ] Ingest → select a Raw source → **Compile with LLM** → a draft appears → **Save** writes a note under `Wiki/` and refreshes the manifest.
- [ ] File → **Backup settings** writes a zip; **Restore settings** reads it back.

- [ ] **Step 3: Commit**

```bash
git add wiki-forge/README.md
git commit -m "docs: add README and manual smoke checklist"
```

---

## Self-Review Notes

- **Spec coverage:** control panel (Task 11 Dashboard + gate), ingest/compile (Task 12), multi-vault (Task 3 + Task 10 switcher), local LLM/Ollama (Task 6 + Task 11), plugin system (Tasks 7–8, all core plugins use it), backup (Task 9 + Task 10 menu), error isolation (Task 8 + defensive `active_vault is None` checks + Ollama health gate in Task 12), testing (every service task). RAG chat intentionally deferred per spec.
- **Type consistency:** `JsonStore`, `Vault`, `VaultManager(store)`, `JobRunner.submit(fn, on_done, on_error)`, `WikiToolService(job_runner)` with `run_sync`/`run_script_sync`/`run`, `OllamaProvider(base_url)`, `PluginContext(plugin, vault_manager, job_runner, wiki_tool, llm, settings, log, ui)`, `PluginHost(plugin_dirs, context_factory, log)` — used identically across tasks.
- **Known ordering note:** Task 10's smoke test starts minimal and is tightened in Task 12 Step 4 once all three core plugins exist. This is called out explicitly in both tasks.
```

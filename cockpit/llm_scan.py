"""Discover LLMs available from this machine (local runtimes + cloud variants).

Pure helpers do the parsing/aggregation; scan_local_llms() is the only impure
entry point and takes all of its I/O dependencies as injectable callables, so
tests run with fakes (mirrors dashboard.run_gate_steps).
"""
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


def parse_ollama_list(text):
    """Return model names (first column) from `ollama list` output.

    Skips the header row, blank lines, and Ollama server log lines (time=...).
    """
    names = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^time=", line):
            continue
        if line.startswith("NAME"):
            continue
        names.append(line.split()[0])
    return names


CLOUD_CATALOG = {
    "anthropic": ["claude-opus", "claude-sonnet", "claude-haiku"],
    "openai": ["gpt-4o", "gpt-4o-mini"],
    "google": ["gemini-2.0-flash", "gemini-1.5-pro"],
    "mistral": ["mistral-large", "mistral-small"],
    "groq": ["llama-3.3-70b"],
}

_ENV_PROVIDERS = {
    "anthropic": ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"],
    "openai": ["OPENAI_API_KEY"],
    "google": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "mistral": ["MISTRAL_API_KEY"],
    "groq": ["GROQ_API_KEY"],
}


def detect_cloud_providers(env, which):
    """Provider keys present via API-key env vars or the `claude` CLI.

    Returns them deduplicated, in CLOUD_CATALOG order.
    """
    found = set()
    for provider, keys in _ENV_PROVIDERS.items():
        if any(env.get(k) for k in keys):
            found.add(provider)
    if which("claude"):
        found.add("anthropic")
    return [p for p in CLOUD_CATALOG if p in found]


def expand_cloud_models(providers):
    """Flatten each provider's catalog variants, in the given order."""
    models = []
    for p in providers:
        models.extend(CLOUD_CATALOG.get(p, []))
    return models


@dataclass
class ScanSections:
    """Collected findings from one machine scan."""
    ollama_status: str = "not installed"
    ollama_models: list = field(default_factory=list)      # ["llama3.2:3b", ...]
    runtimes: list = field(default_factory=list)           # [(name, [entries])]
    weights: list = field(default_factory=list)            # [(path, gb)]
    cli_tools: list = field(default_factory=list)          # [(name, path)]
    cloud: list = field(default_factory=list)              # [(provider, [variants])]


def collect_models(sections):
    """Flat, deduped model list; locals first, cloud last (first-seen order)."""
    ordered = []
    seen = set()

    def add(name):
        if name and name not in seen:
            seen.add(name)
            ordered.append(name)

    for m in sections.ollama_models:
        add(m)
    for _name, entries in sections.runtimes:
        for e in entries:
            add(e)
    for path, _gb in sections.weights:
        add(Path(path).stem)
    for _provider, variants in sections.cloud:
        for v in variants:
            add(v)
    return ordered


def build_report(sections):
    """Human-readable === SECTION === report; every section always present."""
    lines = []

    def section(title):
        lines.append("")
        lines.append(f"=== {title} ===")

    section("OLLAMA (local)")
    lines.append(f"status: {sections.ollama_status}")
    lines.extend(sections.ollama_models or ["(no models)"])

    section("OTHER LOCAL RUNTIMES")
    if sections.runtimes:
        for name, entries in sections.runtimes:
            lines.append(f"{name}: {len(entries)} entries")
    else:
        lines.append("none found")

    section("MODEL WEIGHT FILES")
    if sections.weights:
        for path, gb in sections.weights:
            lines.append(f"{gb:>8.2f} GB  {path}")
    else:
        lines.append("none found")

    section("LLM CLI TOOLS")
    if sections.cli_tools:
        for name, path in sections.cli_tools:
            lines.append(f"{name} -> {path}")
    else:
        lines.append("none found")

    section("CLOUD PROVIDERS")
    if sections.cloud:
        for provider, variants in sections.cloud:
            lines.append(f"{provider}: {', '.join(variants)}")
    else:
        lines.append("none found")

    section("DONE")
    return "\n".join(lines).strip() + "\n"


def scan_local_llms(*, env=None, which=shutil.which, run=subprocess.run, home=None):
    """Scan the machine for LLMs. Returns (report_text, model_names).

    All I/O is via injected callables so tests pass fakes. No individual probe
    failure may raise: each degrades to a 'none/unreachable' line.
    """
    env = os.environ if env is None else env
    home_fn = Path.home if home is None else home
    home_dir = Path(home_fn())
    sections = ScanSections()

    # 1. Ollama
    if which("ollama"):
        try:
            proc = run(["ollama", "list"], capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                sections.ollama_models = parse_ollama_list(proc.stdout or "")
                sections.ollama_status = "ok"
            else:
                sections.ollama_status = "unreachable"
        except Exception:  # noqa: BLE001 - any failure degrades gracefully
            sections.ollama_status = "unreachable"

    # 2. Other local runtimes
    runtime_dirs = {
        "LM Studio": home_dir / ".lmstudio" / "models",
        "LM Studio (cache)": home_dir / ".cache" / "lm-studio" / "models",
        "GPT4All": home_dir / ".cache" / "gpt4all",
        "Jan": home_dir / ".jan" / "models",
    }
    for name, p in runtime_dirs.items():
        try:
            if p.is_dir():
                sections.runtimes.append((name, [c.name for c in p.iterdir()]))
        except OSError:
            pass

    # 3. Loose weight files under home (os.walk skips unreadable dirs and
    #    keeps going, instead of aborting the whole traversal on the first one)
    for dirpath, _dirnames, filenames in os.walk(home_dir, onerror=lambda _e: None):
        for fn in filenames:
            if fn.endswith((".gguf", ".safetensors")):
                f = Path(dirpath) / fn
                try:
                    gb = round(f.stat().st_size / (1024 ** 3), 2)
                except OSError:
                    gb = 0.0
                sections.weights.append((str(f), gb))

    # 4. CLI tools on PATH
    for tool in ("ollama", "claude", "llm", "aichat"):
        path = which(tool)
        if path:
            sections.cli_tools.append((tool, path))

    # 5. Cloud providers -> variants
    for provider in detect_cloud_providers(env, which):
        sections.cloud.append((provider, CLOUD_CATALOG[provider]))

    return build_report(sections), collect_models(sections)

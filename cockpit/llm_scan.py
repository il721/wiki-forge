"""Discover LLMs available from this machine (local runtimes + cloud variants).

Pure helpers do the parsing/aggregation; scan_local_llms() is the only impure
entry point and takes all of its I/O dependencies as injectable callables, so
tests run with fakes (mirrors dashboard.run_gate_steps).
"""
import re


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

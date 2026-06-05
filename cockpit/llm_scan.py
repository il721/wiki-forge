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

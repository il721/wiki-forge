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

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

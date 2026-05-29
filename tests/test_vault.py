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

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

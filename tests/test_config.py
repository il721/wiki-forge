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

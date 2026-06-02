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

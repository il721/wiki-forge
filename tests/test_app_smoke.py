from cockpit.app import MainWindow


def test_mainwindow_loads_core_plugins(qtbot, tmp_path, monkeypatch):
    import cockpit.app as app_mod
    monkeypatch.setattr(app_mod, "config_dir", lambda: tmp_path)
    win = MainWindow()
    qtbot.addWidget(win)
    labels = [win.tabs.tabText(i) for i in range(win.tabs.count())]
    assert "Dashboard" in labels
    assert "LLM Settings" in labels
    assert "Ingest" not in labels

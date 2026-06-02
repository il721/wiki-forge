from cockpit.app import MainWindow
import cockpit.app as app_mod


def test_mainwindow_constructs(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(app_mod, "config_dir", lambda: tmp_path)
    win = MainWindow()
    qtbot.addWidget(win)
    assert win.tabs is not None

"""Wiki-Forge main window: wires services and mounts plugins."""
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QLabel, QPushButton, QTabWidget, QPlainTextEdit, QDockWidget, QFileDialog,
    QMessageBox, QToolBar,
)
from PySide6.QtCore import Qt

from cockpit.config import config_dir, JsonStore
from cockpit.vault import VaultManager
from cockpit.jobs import JobRunner
from cockpit.wiki_tool_service import WikiToolService
from cockpit.llm.ollama import OllamaProvider
from cockpit.plugin import PluginContext
from cockpit.plugin_host import PluginHost
from cockpit.backup import backup_settings, restore_settings


class _UiHost:
    """Adapts plugin mount calls to the window's Qt widgets."""

    def __init__(self, window):
        self.w = window

    def add_tab(self, plugin, widget):
        self.w.tabs.addTab(widget, plugin.name)

    def add_toolbar_action(self, plugin, label, fn):
        act = self.w.toolbar.addAction(label)
        act.triggered.connect(fn)

    def add_dashboard_card(self, plugin, widget):
        self.w.dashboard_cards.append(widget)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wiki-Forge")
        self.resize(1000, 700)
        self.dashboard_cards = []

        cfg = config_dir()
        self.vaults_store = JsonStore(cfg / "vaults.json")
        self.settings_store = JsonStore(cfg / "settings.json")
        self.settings_store.data.setdefault("plugins", {})
        self.settings_store.data.setdefault("ollama_url", "http://localhost:11434")

        self.vault_manager = VaultManager(self.vaults_store)
        self.jobs = JobRunner()
        self.wiki_tool = WikiToolService(self.jobs)
        self.llm = OllamaProvider(self.settings_store.data["ollama_url"])

        self._build_ui()
        self._build_menu()

        plugin_dirs = [
            Path(__file__).resolve().parent.parent / "plugins" / "core",
            config_dir() / "plugins",
        ]
        self.host = PluginHost(plugin_dirs, context_factory=self._make_context,
                               log=self.log)
        self.host.load_all()
        self._refresh_vault_combo()

    # --- UI construction ---------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        layout = QVBoxLayout(central)

        top = QHBoxLayout()
        top.addWidget(QLabel("Vault:"))
        self.vault_combo = QComboBox()
        self.vault_combo.currentIndexChanged.connect(self._on_combo_changed)
        top.addWidget(self.vault_combo, 1)
        add_btn = QPushButton("+ Add vault")
        add_btn.clicked.connect(self._add_vault)
        top.addWidget(add_btn)
        layout.addLayout(top)

        self.toolbar = QToolBar("Actions")
        self.addToolBar(self.toolbar)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        self.log_view = QPlainTextEdit(readOnly=True)
        dock = QDockWidget("Log", self)
        dock.setWidget(self.log_view)
        self.addDockWidget(Qt.BottomDockWidgetArea, dock)

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("File")
        file_menu.addAction("Backup settings…", self._backup)
        file_menu.addAction("Restore settings…", self._restore)
        file_menu.addSeparator()
        file_menu.addAction("Reload plugins", self._reload_plugins)

    # --- plugin wiring -----------------------------------------------------
    def _make_context(self, plugin):
        plugins_cfg = self.settings_store.data["plugins"]
        plugins_cfg.setdefault(plugin.id, {})
        return PluginContext(
            plugin=plugin,
            vault_manager=self.vault_manager,
            job_runner=self.jobs,
            wiki_tool=self.wiki_tool,
            llm=self.llm,
            settings=plugins_cfg[plugin.id],
            log=self.log,
            ui=_UiHost(self),
        )

    # --- vault switcher ----------------------------------------------------
    def _refresh_vault_combo(self):
        self.vault_combo.blockSignals(True)
        self.vault_combo.clear()
        for v in self.vault_manager.vaults:
            self.vault_combo.addItem(v.name, v)
        active = self.vault_manager.active
        if active:
            idx = next((i for i in range(self.vault_combo.count())
                        if self.vault_combo.itemData(i).root == active.root), -1)
            if idx >= 0:
                self.vault_combo.setCurrentIndex(idx)
        self.vault_combo.blockSignals(False)
        if active:
            self.vault_manager.set_active(active)  # fire initial refresh

    def _on_combo_changed(self, idx):
        vault = self.vault_combo.itemData(idx)
        if vault is not None:
            self.vault_manager.set_active(vault)

    def _add_vault(self):
        folder = QFileDialog.getExistingDirectory(self, "Select an LLM Wiki vault folder")
        if not folder:
            return
        try:
            self.vault_manager.add(folder)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid vault", str(exc))
            return
        self._refresh_vault_combo()

    # --- menu actions ------------------------------------------------------
    def _backup(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup settings", "wiki-forge-backup.zip", "Zip (*.zip)")
        if path:
            backup_settings(config_dir(), path)
            self.log(f"Settings backed up to {path}")

    def _restore(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Restore settings", "", "Zip (*.zip)")
        if not path:
            return
        if QMessageBox.question(self, "Restore",
                                "Overwrite current settings with this backup?") \
                == QMessageBox.Yes:
            restore_settings(path, config_dir())
            QMessageBox.information(self, "Restore",
                                    "Restored. Restart Wiki-Forge to apply.")

    def _reload_plugins(self):
        QMessageBox.information(self, "Reload plugins",
                                "Restart Wiki-Forge to load plugin changes.")

    # --- shared services ---------------------------------------------------
    def log(self, msg):
        self.log_view.appendPlainText(str(msg))

    def closeEvent(self, event):
        self.settings_store.save()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

"""LLM Settings plugin: Ollama endpoint, model selection, health check, scan."""
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QComboBox, QPushButton, QLabel,
    QDoubleSpinBox, QListWidget,
)

from cockpit.plugin import Plugin
from cockpit.llm_scan import scan_local_llms


class LlmSettingsPlugin(Plugin):
    id, name, version = "core.llm", "LLM Settings", "1.0.0"

    def activate(self, ctx):
        self.ctx = ctx
        s = ctx.settings
        s.setdefault("compile_model", "llama3.2:3b")
        s.setdefault("chat_model", "llama3.2:3b")
        s.setdefault("temperature", 0.2)

        w = QWidget()
        form = QFormLayout(w)

        self.url = QLineEdit(getattr(ctx.llm, "base_url", "http://localhost:11434"))
        form.addRow("Ollama URL", self.url)

        self.models = QComboBox()
        self.models.setEditable(True)
        self.models.setCurrentText(s["compile_model"])
        form.addRow("Working LLM", self.models)

        self.temp = QDoubleSpinBox()
        self.temp.setRange(0.0, 2.0)
        self.temp.setSingleStep(0.1)
        self.temp.setValue(float(s["temperature"]))
        form.addRow("Temperature", self.temp)

        self.health = QLabel("Unknown")
        check = QPushButton("Check / refresh models")
        check.clicked.connect(self._check)
        form.addRow(check, self.health)

        self.scan_status = QLabel("")
        find = QPushButton("Find LLM")
        find.clicked.connect(self._find_llms)
        form.addRow(find, self.scan_status)

        # Clicking a found model makes it the Working LLM.
        self.found_list = QListWidget()
        self.found_list.itemClicked.connect(
            lambda item: self.models.setCurrentText(item.text()))
        form.addRow(self.found_list)

        save = QPushButton("Save")
        save.clicked.connect(self._save)
        form.addRow(save)

        # Models from the last *saved* Find LLM scan; restored on launch.
        # `_scanned_models` stays None until a new scan runs this session, so a
        # plain Save never overwrites the stored list without a fresh scan.
        self._scanned_models = None
        saved = s.get("found_models", [])
        if saved:
            self._set_found(saved)
            self._merge_models(saved)

        # Make the saved working model the program-wide default for LLM calls.
        ctx.llm.model = s["compile_model"]

        ctx.add_tab(w)

    def _set_found(self, names):
        """Show the discovered model names as clickable rows."""
        self.found_list.clear()
        self.found_list.addItems(names)

    def _merge_models(self, names):
        """Add any new names to the dropdown, preserving the current selection."""
        current = self.models.currentText()
        existing = {self.models.itemText(i) for i in range(self.models.count())}
        for name in names:
            if name not in existing:
                self.models.addItem(name)
                existing.add(name)
        self.models.setCurrentText(current)

    def _check(self):
        self.ctx.llm.base_url = self.url.text().rstrip("/")
        ok = self.ctx.llm.health()
        self.health.setText("Reachable" if ok else "Not reachable")
        if ok:
            self.ctx.run_job(self.ctx.llm.list_models, on_done=self._fill_models)

    def _fill_models(self, names):
        self._merge_models(names)

    def _find_llms(self):
        self.scan_status.setText("Scanning…")
        self.ctx.run_job(
            scan_local_llms, on_done=self._show_scan, on_error=self._scan_failed,
        )

    def _show_scan(self, result):
        report, models = result
        # Raw scan report goes to the Log window; the box lists found model
        # names only, one per line.
        self.ctx.log(report)
        self._set_found(models)
        self._merge_models(models)
        self._scanned_models = models  # marks a fresh scan to persist on Save
        self.scan_status.setText(f"Found {len(models)} model(s).")

    def _scan_failed(self, msg):
        self.scan_status.setText(f"Scan failed: {msg}")
        self.ctx.log(f"Find LLM scan failed: {msg}")

    def _save(self):
        self.ctx.llm.base_url = self.url.text().rstrip("/")
        self.ctx.settings["compile_model"] = self.models.currentText()
        self.ctx.settings["temperature"] = self.temp.value()
        # Apply the chosen model as the default for subsequent LLM actions.
        self.ctx.llm.model = self.models.currentText()
        # Persist found models only when a fresh scan ran this session.
        if self._scanned_models is not None:
            self.ctx.settings["found_models"] = self._scanned_models
        self.ctx.log("LLM settings saved.")

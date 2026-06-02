"""LLM Settings plugin: Ollama endpoint, model selection, health check."""
from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QComboBox, QPushButton, QLabel, QDoubleSpinBox,
)

from cockpit.plugin import Plugin


class LlmSettingsPlugin(Plugin):
    id, name, version = "core.llm", "LLM Settings", "1.0.0"

    def activate(self, ctx):
        self.ctx = ctx
        s = ctx.settings
        s.setdefault("compile_model", "llama3")
        s.setdefault("chat_model", "llama3")
        s.setdefault("temperature", 0.2)

        w = QWidget()
        form = QFormLayout(w)

        self.url = QLineEdit(getattr(ctx.llm, "base_url", "http://localhost:11434"))
        form.addRow("Ollama URL", self.url)

        self.models = QComboBox()
        self.models.setEditable(True)
        self.models.setCurrentText(s["compile_model"])
        form.addRow("Compile model", self.models)

        self.temp = QDoubleSpinBox()
        self.temp.setRange(0.0, 2.0)
        self.temp.setSingleStep(0.1)
        self.temp.setValue(float(s["temperature"]))
        form.addRow("Temperature", self.temp)

        self.health = QLabel("Unknown")
        check = QPushButton("Check / refresh models")
        check.clicked.connect(self._check)
        form.addRow(check, self.health)

        save = QPushButton("Save")
        save.clicked.connect(self._save)
        form.addRow(save)

        ctx.add_tab(w)

    def _check(self):
        self.ctx.llm.base_url = self.url.text().rstrip("/")
        ok = self.ctx.llm.health()
        self.health.setText("Reachable" if ok else "Not reachable")
        if ok:
            self.ctx.run_job(self.ctx.llm.list_models, on_done=self._fill_models)

    def _fill_models(self, names):
        current = self.models.currentText()
        self.models.clear()
        self.models.addItems(names)
        self.models.setCurrentText(current)

    def _save(self):
        self.ctx.llm.base_url = self.url.text().rstrip("/")
        self.ctx.settings["compile_model"] = self.models.currentText()
        self.ctx.settings["temperature"] = self.temp.value()
        self.ctx.log("LLM settings saved.")

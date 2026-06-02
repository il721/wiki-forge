"""Ingest & Compile plugin: raw sources -> LLM-drafted Wiki notes (reviewed)."""
from datetime import date
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QPlainTextEdit, QPushButton,
    QComboBox, QLabel, QMessageBox,
)

from cockpit.plugin import Plugin

FOLDER_FOR_TAG = {
    "concept": "Concepts", "topic": "Topics", "entity": "Entities",
    "project": "Projects", "log": "Logs",
}

COMPILE_PROMPT = (
    "You are compiling a raw source into a concise, reusable wiki note. "
    "Write clear markdown body text only (no frontmatter). "
    "Every claim must be supported by the source.\n\nSOURCE:\n{source}"
)


def build_wiki_note(body, source_rel, tag, today):
    """Compose a compiled Wiki note with schema-correct frontmatter. Pure/testable."""
    fm = (
        "---\n"
        "tags:\n"
        f'  - "{tag}"\n'
        "topics: []\n"
        "status: seed\n"
        f"created: {today}\n"
        f"updated: {today}\n"
        "sources:\n"
        f'  - "{source_rel}"\n'
        "source_count: 1\n"
        "aliases: []\n"
        "---\n\n"
    )
    return fm + body.strip() + "\n"


class IngestPlugin(Plugin):
    id, name, version = "core.ingest", "Ingest", "1.0.0"

    def activate(self, ctx):
        self.ctx = ctx
        w = QWidget()
        outer = QHBoxLayout(w)

        left = QVBoxLayout()
        left.addWidget(QLabel("Raw sources"))
        self.list = QListWidget()
        self.list.currentTextChanged.connect(self._show_source)
        left.addWidget(self.list, 1)
        outer.addLayout(left, 1)

        right = QVBoxLayout()
        self.source_view = QPlainTextEdit(readOnly=True)
        right.addWidget(QLabel("Source"))
        right.addWidget(self.source_view, 1)

        controls = QHBoxLayout()
        self.tag = QComboBox()
        self.tag.addItems(list(FOLDER_FOR_TAG.keys()))
        controls.addWidget(QLabel("Compile as"))
        controls.addWidget(self.tag)
        compile_btn = QPushButton("Compile with LLM")
        compile_btn.clicked.connect(self._compile)
        controls.addWidget(compile_btn)
        right.addLayout(controls)

        self.draft = QPlainTextEdit()
        right.addWidget(QLabel("Draft (review before saving)"))
        right.addWidget(self.draft, 1)
        save_btn = QPushButton("Save to Wiki + update manifest")
        save_btn.clicked.connect(self._save)
        right.addWidget(save_btn)
        outer.addLayout(right, 2)

        ctx.add_tab(w)
        ctx.on_vault_changed(self._reload_sources)

    def _reload_sources(self, vault):
        self.list.clear()
        if vault is None:
            return
        for p in sorted(vault.raw_sources.glob("*.md")):
            self.list.addItem(p.name)

    def _current_source_path(self):
        vault = self.ctx.active_vault
        item = self.list.currentItem()
        if vault is None or item is None:
            return None
        return vault.raw_sources / item.text()

    def _show_source(self, _name):
        p = self._current_source_path()
        if p and p.exists():
            self.source_view.setPlainText(p.read_text(encoding="utf-8"))

    def _compile(self):
        p = self._current_source_path()
        if p is None:
            return
        if not self.ctx.llm.health():
            QMessageBox.warning(self.draft, "Ollama",
                                "Ollama is not reachable. Check LLM Settings.")
            return
        prompt = COMPILE_PROMPT.format(source=p.read_text(encoding="utf-8"))
        model = self.ctx.settings.get("compile_model", "llama3")
        self.draft.setPlainText("Compiling…")
        self.ctx.run_job(
            lambda: self.ctx.llm.generate(prompt, model=model),
            on_done=self.draft.setPlainText,
            on_error=lambda e: self.draft.setPlainText(f"Error: {e}"),
        )

    def _save(self):
        vault = self.ctx.active_vault
        src = self._current_source_path()
        if vault is None or src is None:
            return
        tag = self.tag.currentText()
        source_rel = src.relative_to(vault.root).as_posix()
        note = build_wiki_note(self.draft.toPlainText(), source_rel, tag,
                               date.today().isoformat())
        dest_dir = vault.wiki / FOLDER_FOR_TAG[tag]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        dest.write_text(note, encoding="utf-8")
        self.ctx.log(f"Wrote {dest}")
        # Refresh manifest + lint via the deterministic tooling.
        self.ctx.wiki_tool.run("source-scan", "--update", "--accept-covered",
                               on_done=self.ctx.log)

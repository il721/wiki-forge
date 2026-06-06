from cockpit.llm_scan import (
    parse_ollama_list, CLOUD_CATALOG, detect_cloud_providers, expand_cloud_models,
    ScanSections, collect_models, build_report, scan_local_llms,
)


def test_parse_ollama_list_extracts_first_column():
    text = (
        "NAME            ID    SIZE   MODIFIED\n"
        "llama3.2:3b     abc   2.0GB  1 day ago\n"
        "qwen2.5:7b      def   4.7GB  2 days ago\n"
    )
    assert parse_ollama_list(text) == ["llama3.2:3b", "qwen2.5:7b"]


def test_parse_ollama_list_skips_log_blank_and_header():
    text = "time=2026-01-01 level=INFO msg=starting\n\nllama3.2:3b  abc 2GB\n"
    assert parse_ollama_list(text) == ["llama3.2:3b"]


def test_parse_ollama_list_empty():
    assert parse_ollama_list("") == []


def test_parse_ollama_list_keeps_model_named_like_header():
    assert parse_ollama_list("namelike:1b  abc  2GB\n") == ["namelike:1b"]


def test_detect_cloud_providers_from_env_keys():
    env = {"OPENAI_API_KEY": "sk-x", "GOOGLE_API_KEY": "y"}
    assert detect_cloud_providers(env, lambda c: None) == ["openai", "google"]


def test_detect_cloud_providers_claude_cli_implies_anthropic():
    which = lambda c: "C:/claude.exe" if c == "claude" else None
    assert detect_cloud_providers({}, which) == ["anthropic"]


def test_detect_cloud_providers_dedupes_keeping_catalog_order():
    env = {"ANTHROPIC_API_KEY": "k", "GROQ_API_KEY": "g"}
    which = lambda c: "x" if c == "claude" else None  # also anthropic
    assert detect_cloud_providers(env, which) == ["anthropic", "groq"]


def test_expand_cloud_models_flattens_in_order():
    assert expand_cloud_models(["anthropic", "openai"]) == [
        "claude-opus", "claude-sonnet", "claude-haiku", "gpt-4o", "gpt-4o-mini",
    ]


def test_collect_models_locals_before_cloud_deduped():
    s = ScanSections(
        ollama_models=["llama3.2:3b", "qwen2.5:7b"],
        runtimes=[("LM Studio", ["mistral-7b"])],
        weights=[("C:/x/phi-2.gguf", 1.6)],
        cloud=[("anthropic", ["claude-opus"]), ("openai", ["gpt-4o"])],
    )
    assert collect_models(s) == [
        "llama3.2:3b", "qwen2.5:7b", "mistral-7b", "phi-2",
        "claude-opus", "gpt-4o",
    ]


def test_collect_models_drops_repeats():
    s = ScanSections(ollama_models=["a", "a"], cloud=[("openai", ["a", "gpt-4o"])])
    assert collect_models(s) == ["a", "gpt-4o"]


def test_build_report_has_every_section_even_when_empty():
    text = build_report(ScanSections())
    for header in ["OLLAMA", "OTHER LOCAL RUNTIMES", "MODEL WEIGHT FILES",
                   "LLM CLI TOOLS", "CLOUD PROVIDERS"]:
        assert header in text
    assert "none found" in text


def test_scan_local_llms_combines_all_sources(tmp_path):
    def fake_which(c):
        return {"ollama": "/usr/bin/ollama", "claude": "/usr/bin/claude"}.get(c)

    class FakeProc:
        returncode = 0
        stdout = "NAME ID SIZE\nllama3.2:3b a 2GB\n"

    def fake_run(args, **kwargs):
        return FakeProc()

    report, models = scan_local_llms(
        env={"OPENAI_API_KEY": "x"},
        which=fake_which, run=fake_run, home=lambda: tmp_path,
    )
    assert "llama3.2:3b" in models          # from fake ollama
    assert "claude-opus" in models          # claude CLI -> anthropic
    assert "gpt-4o" in models               # OPENAI_API_KEY -> openai
    assert "=== OLLAMA" in report
    assert "ollama ->" in report            # cli tools section


def test_scan_local_llms_survives_ollama_failure(tmp_path):
    def fake_run(args, **kwargs):
        raise OSError("boom")

    report, models = scan_local_llms(
        env={}, which=lambda c: "/x" if c == "ollama" else None,
        run=fake_run, home=lambda: tmp_path,
    )
    assert "unreachable" in report
    assert models == []


def test_scan_local_llms_finds_weight_files(tmp_path):
    # Two .gguf files in different subdirs; both must be discovered (traversal
    # must not stop early). A non-weight file is ignored.
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "phi-2.gguf").write_bytes(b"x")
    (tmp_path / "b" / "mistral-7b.safetensors").write_bytes(b"y")
    (tmp_path / "a" / "notes.txt").write_text("ignore me")

    report, models = scan_local_llms(
        env={}, which=lambda c: None, run=lambda *a, **k: None,
        home=lambda: tmp_path,
    )
    assert "phi-2" in models
    assert "mistral-7b" in models
    assert "notes" not in models
    assert "MODEL WEIGHT FILES" in report


def test_check_refresh_models_is_additive(qtbot):
    from plugins.core.llm_settings import LlmSettingsPlugin

    class FakeLlm:
        base_url = "http://localhost:11434"

    class FakeCtx:
        def __init__(self):
            self.settings = {}
            self.llm = FakeLlm()
            self.logs = []
            self.tab = None
        def run_job(self, fn, on_done=None, on_error=None):
            pass
        def add_tab(self, w):
            self.tab = w
        def log(self, m):
            self.logs.append(m)

    plugin = LlmSettingsPlugin()
    ctx = FakeCtx()
    plugin.activate(ctx)
    qtbot.addWidget(ctx.tab)

    # A scan added a cloud model; a later Ollama refresh must NOT wipe it.
    plugin._show_scan(("REPORT", ["claude-opus"]))
    plugin._fill_models(["llama3.2:3b", "qwen2.5:7b"])

    items = [plugin.models.itemText(i) for i in range(plugin.models.count())]
    assert "claude-opus" in items          # survived the refresh
    assert "llama3.2:3b" in items
    assert "qwen2.5:7b" in items
    # no duplicates
    assert len(items) == len(set(items))


def test_find_llm_relabels_and_merges_dropdown(qtbot):
    from PySide6.QtWidgets import QLabel
    from plugins.core.llm_settings import LlmSettingsPlugin

    class FakeLlm:
        base_url = "http://localhost:11434"

    class FakeCtx:
        def __init__(self):
            self.settings = {}
            self.llm = FakeLlm()
            self.logs = []
            self.tab = None
        def run_job(self, fn, on_done=None, on_error=None):
            pass
        def add_tab(self, w):
            self.tab = w
        def log(self, m):
            self.logs.append(m)

    plugin = LlmSettingsPlugin()
    ctx = FakeCtx()
    plugin.activate(ctx)
    qtbot.addWidget(ctx.tab)

    # Relabel: row reads "Working LLM", not "Compile model".
    label_texts = [lab.text() for lab in ctx.tab.findChildren(QLabel)]
    assert "Working LLM" in label_texts
    assert "Compile model" not in label_texts

    # Merge: scan results land in the combo + report, selection preserved.
    plugin._show_scan(("REPORT BODY", ["llama3.2:3b", "claude-opus"]))
    items = [plugin.models.itemText(i) for i in range(plugin.models.count())]
    assert "llama3.2:3b" in items
    assert "claude-opus" in items
    # The found-models list holds only the model names, one per row...
    found = [plugin.found_list.item(i).text()
             for i in range(plugin.found_list.count())]
    assert found == ["llama3.2:3b", "claude-opus"]
    # ...while the raw scan report goes to the Log window.
    assert "REPORT BODY" in ctx.logs
    assert plugin.models.currentText() == "llama3.2:3b"


class _PersistCtx:
    """Minimal ctx whose `settings` dict survives across activations."""

    def __init__(self, settings):
        class FakeLlm:
            base_url = "http://localhost:11434"
        self.settings = settings
        self.llm = FakeLlm()
        self.logs = []
        self.tab = None

    def run_job(self, fn, on_done=None, on_error=None):
        pass

    def add_tab(self, w):
        self.tab = w

    def log(self, m):
        self.logs.append(m)


def test_found_models_loaded_on_activate(qtbot):
    from plugins.core.llm_settings import LlmSettingsPlugin

    plugin = LlmSettingsPlugin()
    ctx = _PersistCtx({"found_models": ["qwen2.5:7b", "claude-opus"]})
    plugin.activate(ctx)
    qtbot.addWidget(ctx.tab)

    # The saved names repopulate the list and the dropdown on load.
    found = [plugin.found_list.item(i).text()
             for i in range(plugin.found_list.count())]
    assert found == ["qwen2.5:7b", "claude-opus"]
    items = [plugin.models.itemText(i) for i in range(plugin.models.count())]
    assert "qwen2.5:7b" in items
    assert "claude-opus" in items


def test_clicking_found_model_selects_working_llm(qtbot):
    from plugins.core.llm_settings import LlmSettingsPlugin

    plugin = LlmSettingsPlugin()
    ctx = _PersistCtx({})
    plugin.activate(ctx)
    qtbot.addWidget(ctx.tab)

    plugin._show_scan(("RAW", ["llama3.2:3b", "claude-opus"]))

    # Clicking a model fills the Working LLM field...
    item = plugin.found_list.item(1)
    plugin.found_list.itemClicked.emit(item)
    assert plugin.models.currentText() == "claude-opus"

    # ...and Save remembers it as the working model, applying it as the
    # provider default for subsequent actions in the program.
    plugin._save()
    assert ctx.settings["compile_model"] == "claude-opus"
    assert ctx.llm.model == "claude-opus"


def test_saved_working_model_applied_on_load(qtbot):
    from plugins.core.llm_settings import LlmSettingsPlugin

    plugin = LlmSettingsPlugin()
    ctx = _PersistCtx({"compile_model": "qwen2.5:7b"})
    plugin.activate(ctx)
    qtbot.addWidget(ctx.tab)

    # The saved working model loads into the field and becomes the default.
    assert plugin.models.currentText() == "qwen2.5:7b"
    assert ctx.llm.model == "qwen2.5:7b"


def test_save_persists_found_models_only_after_scan(qtbot):
    from plugins.core.llm_settings import LlmSettingsPlugin

    plugin = LlmSettingsPlugin()
    ctx = _PersistCtx({"found_models": ["old-model"]})
    plugin.activate(ctx)
    qtbot.addWidget(ctx.tab)

    # Save with no new scan: the stored list must stay unchanged.
    plugin._save()
    assert ctx.settings["found_models"] == ["old-model"]

    # A fresh scan + Save: the stored list updates to the new findings.
    plugin._show_scan(("RAW", ["llama3.2:3b", "claude-haiku"]))
    plugin._save()
    assert ctx.settings["found_models"] == ["llama3.2:3b", "claude-haiku"]

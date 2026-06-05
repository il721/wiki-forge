from cockpit.llm_scan import parse_ollama_list


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


from cockpit.llm_scan import (
    CLOUD_CATALOG, detect_cloud_providers, expand_cloud_models,
)


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


from cockpit.llm_scan import ScanSections, collect_models, build_report


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

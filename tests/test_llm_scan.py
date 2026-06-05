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

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

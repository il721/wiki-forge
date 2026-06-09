from cockpit.llm.ollama import OllamaProvider


class _FakeResp:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


def test_health_true_when_tags_ok(monkeypatch):
    monkeypatch.setattr(
        "cockpit.llm.ollama.requests.get", lambda *a, **k: _FakeResp(200))
    assert OllamaProvider().health() is True


def test_health_false_on_exception(monkeypatch):
    import requests

    def boom(*a, **k):
        raise requests.RequestException("down")

    monkeypatch.setattr("cockpit.llm.ollama.requests.get", boom)
    assert OllamaProvider().health() is False


def test_list_models_parses_names(monkeypatch):
    payload = {"models": [{"name": "llama3"}, {"name": "qwen2"}]}
    monkeypatch.setattr(
        "cockpit.llm.ollama.requests.get", lambda *a, **k: _FakeResp(200, payload))
    assert OllamaProvider().list_models() == ["llama3", "qwen2"]


def test_generate_returns_response_field(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["json"] = json
        return _FakeResp(200, {"response": "hello world"})

    monkeypatch.setattr("cockpit.llm.ollama.requests.post", fake_post)
    out = OllamaProvider().generate("hi", model="llama3")
    assert out == "hello world"
    assert captured["json"]["model"] == "llama3"
    assert captured["json"]["stream"] is False


def test_generate_defaults_to_installed_model(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["json"] = json
        return _FakeResp(200, {"response": "x"})

    monkeypatch.setattr("cockpit.llm.ollama.requests.post", fake_post)
    OllamaProvider().generate("hi")  # no model -> falls back to the default
    assert captured["json"]["model"] == "llama3.2:3b"


def test_generate_uses_configured_default_model(monkeypatch):
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["json"] = json
        return _FakeResp(200, {"response": "x"})

    monkeypatch.setattr("cockpit.llm.ollama.requests.post", fake_post)
    OllamaProvider(model="qwen2.5:7b").generate("hi")  # uses the chosen default
    assert captured["json"]["model"] == "qwen2.5:7b"


def test_generate_nests_options_under_options_key(monkeypatch):
    """Runtime params must go under Ollama's `options` key, not top level."""
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["json"] = json
        return _FakeResp(200, {"response": "x"})

    monkeypatch.setattr("cockpit.llm.ollama.requests.post", fake_post)
    OllamaProvider().generate("hi", model="llama3.2:3b",
                              options={"num_ctx": 8192, "temperature": 0.2})
    assert captured["json"]["options"] == {"num_ctx": 8192, "temperature": 0.2}
    # Must NOT leak to the top level, where Ollama would ignore it.
    assert "num_ctx" not in captured["json"]
    assert "temperature" not in captured["json"]


def test_generate_auto_adds_num_gpu_for_qwen35(monkeypatch):
    """qwen3_5 mis-estimates VRAM and falls to CPU unless all layers forced."""
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["json"] = json
        return _FakeResp(200, {"response": "x"})

    monkeypatch.setattr("cockpit.llm.ollama.requests.post", fake_post)
    OllamaProvider().generate("hi", model="hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M")
    assert captured["json"]["options"]["num_gpu"] == 99


def test_generate_respects_explicit_num_gpu_for_qwen35(monkeypatch):
    """An explicit num_gpu from the caller is never overridden by the default."""
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["json"] = json
        return _FakeResp(200, {"response": "x"})

    monkeypatch.setattr("cockpit.llm.ollama.requests.post", fake_post)
    OllamaProvider().generate("hi", model="qwen3.5:4b",
                              options={"num_gpu": 20})
    assert captured["json"]["options"]["num_gpu"] == 20


def test_generate_no_auto_num_gpu_for_other_models(monkeypatch):
    """Models that fit normally must not get the qwen3_5 workaround."""
    captured = {}

    def fake_post(url, json=None, timeout=None):
        captured["json"] = json
        return _FakeResp(200, {"response": "x"})

    monkeypatch.setattr("cockpit.llm.ollama.requests.post", fake_post)
    OllamaProvider().generate("hi", model="llama3.2:3b")
    assert "num_gpu" not in captured["json"].get("options", {})

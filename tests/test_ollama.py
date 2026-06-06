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

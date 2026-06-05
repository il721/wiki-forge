"""Ollama implementation of LLMProvider (http://localhost:11434)."""
import requests

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url="http://localhost:11434", timeout=120):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        r = requests.get(f"{self.base_url}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]

    def generate(self, prompt: str, model: str | None = None, **opts) -> str:
        payload = {"model": model or "llama3.2:3b", "prompt": prompt, "stream": False}
        payload.update(opts)
        r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("response", "")

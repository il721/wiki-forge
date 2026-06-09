"""Ollama implementation of LLMProvider (http://localhost:11434)."""
import requests

from .base import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self, base_url="http://localhost:11434", model="llama3.2:3b",
                 timeout=120):
        self.base_url = base_url.rstrip("/")
        self.model = model
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
        model = model or self.model
        payload = {"model": model, "prompt": prompt, "stream": False}
        payload.update(opts)  # runtime params belong under opts["options"]
        self._apply_model_defaults(model, payload)
        r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json().get("response", "")

    @staticmethod
    def _apply_model_defaults(model: str, payload: dict) -> None:
        """Force full GPU offload for the qwen3_5 arch.

        Ollama over-estimates qwen3_5's VRAM footprint and silently offloads it
        to the CPU (~7 tok/s on this hardware); pinning all layers to the GPU
        loads it at ~3GB / 100% GPU. A caller-supplied num_gpu always wins.
        """
        name = model.lower()
        if "qwen3.5" in name or "qwen3_5" in name:
            payload.setdefault("options", {}).setdefault("num_gpu", 99)

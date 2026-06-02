"""The provider contract every LLM backend implements."""
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def health(self) -> bool:
        """True if the backend is reachable."""

    @abstractmethod
    def list_models(self) -> list[str]:
        """Available model names."""

    @abstractmethod
    def generate(self, prompt: str, model: str | None = None, **opts) -> str:
        """Return the model's completion for prompt."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolSchema:
    """A single tool exposed to the model."""
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any] = field(default=lambda **kw: None)


class ProviderError(Exception):
    """Raised when a provider fails (rate limit, network, etc)."""


class ProviderUnavailable(ProviderError):
    """Raised when the provider is hit with a rate limit / is down, so the
    router can fall back to another provider."""


class Provider(ABC):
    """Abstract interface every AI provider must implement. The rest of the
    application only talks to this interface via the router."""

    name: str = "base"

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema] | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Run a chat completion. messages is OpenAI-style history.

        Returns a normalized dict:
            {"content": str | None,
             "tool_calls": [{"id","name","arguments"(dict)}]}
        """
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

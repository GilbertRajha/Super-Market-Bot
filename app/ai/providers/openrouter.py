from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from .base import Provider, ProviderError, ProviderUnavailable, ToolSchema


class OpenRouterProvider(Provider):
    """Provider wrapper around OpenRouter's OpenAI-compatible API.

    OpenRouter exposes the /openrouter/free router (and many free models) and
    supports tool calling. The base URL is OpenRouter's, so any configured
    model name that OpenRouter routes is usable.
    """

    name = "openrouter"
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key: str, default_model: str | None = None):
        self._default_model = default_model or ""
        self._client = OpenAI(
            base_url=self.BASE_URL,
            api_key=api_key,
        )

    @staticmethod
    def _to_openai_tools(tools: list[ToolSchema]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in tools
        ]

    def _normalize(self, raw: Any) -> dict[str, Any]:
        message = raw.choices[0].message
        tool_calls: list[dict[str, Any]] = []
        for tc in message.tool_calls or []:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(
                {"id": tc.id, "name": tc.function.name, "arguments": args}
            )
        return {
            "content": message.content,
            "tool_calls": tool_calls,
        }

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema] | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = self._to_openai_tools(tools)
        if temperature is not None:
            kwargs["temperature"] = temperature

        try:
            resp = self._client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - surface as ProviderUnavailable
            msg = str(exc).lower()
            if any(k in msg for k in ("429", "rate", "quota", "limit", "timeout", "connection")):
                raise ProviderUnavailable(f"OpenRouter unavailable: {exc}") from exc
            raise ProviderError(f"OpenRouter request failed: {exc}") from exc

        return self._normalize(resp)

    def close(self) -> None:
        self._client.close()

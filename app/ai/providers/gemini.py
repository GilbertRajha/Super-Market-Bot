from __future__ import annotations

import json
from typing import Any

import google.generativeai as genai

from .base import Provider, ProviderError, ProviderUnavailable, ToolSchema


class GeminiProvider(Provider):
    """Provider wrapper around Google Gemini.

    Uses google-generativeai. Converts our normalized tool schemas into Gemini
    function declarations and normalizes responses back into the shared shape.
    """

    name = "gemini"

    def __init__(self, api_key: str, default_model: str | None = None):
        genai.configure(api_key=api_key)
        self._default_model = default_model or ""
        self._model = self._default_model

    @staticmethod
    def _to_gemini_tools(tools: list[ToolSchema]) -> list[dict[str, Any]]:
        declarations = []
        for t in tools:
            params = dict(t.parameters)
            schema = params.get("properties", {})
            required = params.get("required", [])
            declarations.append(
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": {
                        "type": "OBJECT",
                        "properties": schema,
                        "required": required,
                    },
                }
            )
        return [{"function_declarations": declarations}]

    @staticmethod
    def _to_gemini_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            role = m.get("role")
            if role == "system":
                # Gemini has no system role; fold into first user turn.
                if out:
                    out[-1]["parts"].append(f"[system] {m['content']}")
                else:
                    out.append({"role": "user", "parts": [f"[system] {m['content']}"]})
                continue
            g_role = "model" if role == "assistant" else "user"
            parts: list[Any] = []
            if m.get("content"):
                parts.append(str(m["content"]))
            for tc in m.get("tool_calls", []) or []:
                fn = tc.get("function", tc)
                parts.append(
                    {
                        "function_call": {
                            "name": fn.get("name"),
                            "args": fn.get("arguments", {}),
                        }
                    }
                )
            # tool results come as role=tool; gemini wants them as function_response
            if role == "tool":
                out.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "function_response": {
                                    "name": m.get("name", ""),
                                    "response": {"result": m.get("content", "")},
                                }
                            }
                        ],
                    }
                )
                continue
            out.append({"role": g_role, "parts": parts})
        return out

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolSchema] | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        model_name = model or self._model
        model = genai.GenerativeModel(model_name)

        request: dict[str, Any] = {}
        if tools:
            request["tools"] = self._to_gemini_tools(tools)
        if temperature is not None:
            request["generation_config"] = {"temperature": temperature}

        try:
            resp = model.generate_content(
                self._to_gemini_messages(messages),
                **request,
            )
        except Exception as exc:  # noqa: BLE001
            msg = str(exc).lower()
            if any(k in msg for k in ("429", "quota", "limit", "resource exhausted", "deadline", "unavailable")):
                raise ProviderUnavailable(f"Gemini unavailable: {exc}") from exc
            raise ProviderError(f"Gemini request failed: {exc}") from exc

        return self._normalize(resp)

    @staticmethod
    def _normalize(resp: Any) -> dict[str, Any]:
        content: str | None = None
        tool_calls: list[dict[str, Any]] = []
        try:
            for part in resp.candidates[0].content.parts:
                if part.text:
                    content = (content or "") + part.text
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    args = GeminiProvider._proto_args(fc.args)
                    tool_calls.append(
                        {"id": fc.name, "name": fc.name, "arguments": args}
                    )
        except Exception:  # noqa: BLE001
            content = str(resp)
        return {"content": content, "tool_calls": tool_calls}

    @staticmethod
    def _proto_args(args: Any) -> dict[str, Any]:
        try:
            from google.protobuf.json_format import MessageToJson

            return json.loads(MessageToJson(args))
        except Exception:  # noqa: BLE001
            try:
                return {k: v for k, v in args.items()}
            except Exception:  # noqa: BLE001
                return {}

    def close(self) -> None:
        pass

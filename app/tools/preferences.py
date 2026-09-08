from __future__ import annotations

from typing import Any

from ..database.repositories.preferences import PreferenceRepository
from .registry import ToolContext


def build(ctx: ToolContext) -> dict[str, dict[str, Any]]:
    repo = PreferenceRepository()

    def get_preference(key: str) -> dict[str, Any]:
        value = repo.get(ctx.telegram_id, key)
        if value is None:
            return {"key": key, "value": None}
        return {"key": key, "value": value}

    def set_preference(key: str, value: str) -> dict[str, Any]:
        repo.set(ctx.telegram_id, key, value)
        return {"ok": True, "key": key, "value": value, "message": "Preference saved."}

    def list_preferences() -> dict[str, str]:
        return repo.get_all(ctx.telegram_id)

    return {
        "get_preference": {
            "description": "Get a stored user preference (e.g. default_payment, shop_name).",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
            "handler": get_preference,
        },
        "set_preference": {
            "description": "Store a user preference persistently (e.g. 'Always use UPI' -> default_payment=upi).",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["key", "value"],
            },
            "handler": set_preference,
        },
        "list_preferences": {
            "description": "List all saved preferences for the user.",
            "parameters": {"type": "object", "properties": {}},
            "handler": list_preferences,
        },
    }
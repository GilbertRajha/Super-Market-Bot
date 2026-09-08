from __future__ import annotations

from typing import Any

from ..supabase import get_db


class PreferenceRepository:
    """Persistent per-user memory (default payment method, shop name, etc.)."""

    def __init__(self) -> None:
        self._db = get_db()

    def get(self, telegram_id: int, key: str) -> str | None:
        resp = (
            self._db.db.from_("preferences")
            .select("value")
            .eq("telegram_id", telegram_id)
            .eq("key", key)
            .limit(1)
            .execute()
        )
        data = resp.data or []
        return data[0]["value"] if data else None

    def get_all(self, telegram_id: int) -> dict[str, str]:
        resp = (
            self._db.db.from_("preferences")
            .select("key", "value")
            .eq("telegram_id", telegram_id)
            .execute()
        )
        return {row["key"]: row["value"] for row in (resp.data or [])}

    def set(self, telegram_id: int, key: str, value: str) -> None:
        self._db.db.from_("preferences").upsert(
            {"telegram_id": telegram_id, "key": key, "value": value},
            on_conflict="telegram_id,key",
        ).execute()

    def delete(self, telegram_id: int, key: str) -> None:
        self._db.db.from_("preferences").delete().eq("telegram_id", telegram_id).eq("key", key).execute()
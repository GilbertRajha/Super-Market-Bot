from __future__ import annotations

import uuid
from typing import Any

from ..supabase import get_db


class IdempotencyRepository:
    """One-shot guard against duplicate operations (double-bill, etc.).

    The (telegram_id, idem_key) unique constraint is the safety net; this
    repository performs an insert-or-conflict so concurrent duplicate requests
    for the same key cannot both proceed.
    """

    def __init__(self) -> None:
        self._db = get_db()

    @staticmethod
    def new_key() -> str:
        return uuid.uuid4().hex

    def acquire(
        self, telegram_id: int, operation: str, idem_key: str, payload: dict[str, Any] | None = None
    ) -> bool:
        """Returns True if this (telegram_id, idem_key) is new and acquired;
        False if it already exists (i.e. duplicate operation)."""
        try:
            self._db.db.from_("idempotency_keys").insert(
                {
                    "telegram_id": telegram_id,
                    "idem_key": idem_key,
                    "operation": operation,
                    "payload": payload,
                },
                returning="minimal",
            ).execute()
            return True
        except Exception:
            return False

    def store_result(self, telegram_id: int, idem_key: str, result: dict[str, Any]) -> None:
        self._db.db.from_("idempotency_keys").update({"result": result}).eq(
            "telegram_id", telegram_id
        ).eq("idem_key", idem_key).execute()

    def get_result(self, telegram_id: int, idem_key: str) -> dict[str, Any] | None:
        resp = (
            self._db.db.from_("idempotency_keys")
            .select("result")
            .eq("telegram_id", telegram_id)
            .eq("idem_key", idem_key)
            .limit(1)
            .execute()
        )
        data = resp.data or []
        return (data[0] or {}).get("result") if data else None
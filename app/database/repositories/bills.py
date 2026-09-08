from __future__ import annotations

from typing import Any

from ..supabase import get_db


class BillRepository:
    """Bills, bill sessions, bill items + finalize RPC."""

    def __init__(self) -> None:
        self._db = get_db()

    # ------------------------------------------------------------ sessions
    def get_or_create_open_session(self, telegram_id: int) -> dict[str, Any]:
        """Fetch the user's open draft session or create one.

        A unique partial index enforces one open session per telegram_id.
        """
        resp = (
            self._db.db.from_("bill_sessions")
            .select("*")
            .eq("telegram_id", telegram_id)
            .eq("status", "open")
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        created = (
            self._db.db.from_("bill_sessions")
            .insert({"telegram_id": telegram_id, "status": "open"})
            .execute()
        )
        return (created.data or [{}])[0]

    def close_session(self, session_id: int, status: str = "finalized") -> None:
        self._db.db.from_("bill_sessions").update({"status": status}).eq("id", session_id).execute()

    # ---------------------------------------------------------------- bills
    def insert_bill(self, session_id: int) -> dict[str, Any]:
        resp = (
            self._db.db.from_("bills")
            .insert(
                {
                    "session_id": session_id,
                    "status": "draft",
                    "payment_method": None,
                }
            )
            .execute()
        )
        return (resp.data or [{}])[0]

    def get(self, bill_id: int) -> dict[str, Any] | None:
        resp = (
            self._db.db.from_("bills")
            .select("*")
            .eq("id", bill_id)
            .limit(1)
            .execute()
        )
        data = resp.data or []
        return data[0] if data else None

    def get_by_number(self, bill_number: str) -> dict[str, Any] | None:
        resp = (
            self._db.db.from_("bills")
            .select("*")
            .eq("bill_number", bill_number)
            .limit(1)
            .execute()
        )
        data = resp.data or []
        return data[0] if data else None

    def get_latest(self, limit: int = 10) -> list[dict[str, Any]]:
        resp = (
            self._db.db.from_("bills")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []

    def set_customer(self, bill_id: int, customer_id: int | None) -> dict[str, Any]:
        data = self._db.db.from_("bills").update({"customer_id": customer_id}).eq("id", bill_id).execute()
        return (data.data or [{}])[0]

    def set_payment_method(self, bill_id: int, method: str | None) -> dict[str, Any]:
        data = self._db.db.from_("bills").update({"payment_method": method}).eq("id", bill_id).execute()
        return (data.data or [{}])[0]

    # ------------------------------------------------------------ bill items
    def get_items(self, bill_id: int) -> list[dict[str, Any]]:
        resp = (
            self._db.db.from_("bill_items")
            .select("*")
            .eq("bill_id", bill_id)
            .order("id", desc=False)
            .execute()
        )
        return resp.data or []

    # ------------------------------------------------------------- finalize
    def finalize(
        self,
        bill_id: int,
        items: list[dict[str, Any]],
        paid: float = 0.0,
        payment_method: str = "cash",
    ) -> dict[str, Any]:
        resp = self._db.db.rpc(
            "finalize_bill_rpc",
            {
                "p_bill_id": bill_id,
                "p_items": items,
                "p_paid": paid,
                "p_payment_method": payment_method,
            },
        ).execute()
        return resp.data or {}
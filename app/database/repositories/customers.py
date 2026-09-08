from __future__ import annotations

from typing import Any

from ..supabase import get_db


class CustomerRepository:
    """Customers + khata ledger."""

    def __init__(self) -> None:
        self._db = get_db()

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        q = (query or "").strip()
        resp = self._db.db.from_("customers").select("*").ilike("name", f"%{q}%").limit(limit).execute()
        return resp.data or []

    def get(self, customer_id: int) -> dict[str, Any] | None:
        resp = (
            self._db.db.from_("customers")
            .select("*")
            .eq("id", customer_id)
            .limit(1)
            .execute()
        )
        data = resp.data or []
        return data[0] if data else None

    def create(self, name: str, phone: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name}
        if phone:
            payload["phone"] = phone
        resp = self._db.db.from_("customers").insert(payload).execute()
        return (resp.data or [{}])[0]

    def record_payment(self, customer_id: int, amount: float, method: str = "cash") -> dict[str, Any]:
        resp = self._db.db.rpc(
            "record_khata_payment_rpc",
            {
                "p_customer_id": customer_id,
                "p_amount": amount,
                "p_method": method,
            },
        ).execute()
        return resp.data or {}

    def get_balance(self, customer_id: int) -> dict[str, Any]:
        resp = self._db.db.rpc("get_khata_balance_rpc", {"p_customer_id": customer_id}).execute()
        return resp.data or {"balance": 0}

    def history(self, customer_id: int, limit: int = 20) -> list[dict[str, Any]]:
        resp = (
            self._db.db.from_("khata_transactions")
            .select("*")
            .eq("customer_id", customer_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return resp.data or []
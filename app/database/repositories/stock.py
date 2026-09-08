from __future__ import annotations

from typing import Any

from ..supabase import get_db


class StockRepository:
    """Stock movements + RPC for receive stock."""

    def __init__(self) -> None:
        self._db = get_db()

    def receive_stock(
        self, product_id: int, qty: float, unit_cost: float | None = None
    ) -> dict[str, Any]:
        resp = self._db.db.rpc(
            "receive_stock_rpc",
            {
                "p_product_id": product_id,
                "p_qty": qty,
                "p_unit_cost": unit_cost,
            },
        ).execute()
        return resp.data or {}

    def movements(
        self, product_id: int | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        query = (
            self._db.db.from_("stock_movements")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if product_id is not None:
            query = query.eq("product_id", product_id)
        resp = query.execute()
        return resp.data or []
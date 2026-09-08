from __future__ import annotations

from typing import Any

from ..supabase import get_db


class AnalyticsRepository:
    """Read-model queries for analytics (numbers are computed here, not by AI)."""

    def __init__(self) -> None:
        self._db = get_db()

    def daily_sales(self, days: int = 7) -> list[dict[str, Any]]:
        """Daily sales totals for the last N days (finalized bills)."""
        resp = self._db.db.rpc(
            "daily_sales",
            {"p_days": days},
        ).execute()
        return resp.data or []

    def sales_summary(self, days: int = 7) -> dict[str, float]:
        resp = self._db.db.rpc("sales_summary", {"p_days": days}).execute()
        data = resp.data or []
        row = data[0] if isinstance(data, list) else data or {}
        return {
            "total_sales": float(row.get("total_sales", 0)),
            "gst_collected": float(row.get("gst_collected", 0)),
            "bill_count": float(row.get("bill_count", 0)),
        }

    def top_products(self, days: int = 7, limit: int = 10) -> list[dict[str, Any]]:
        resp = self._db.db.rpc("top_products", {"p_days": days, "p_limit": limit}).execute()
        return resp.data or []

    def payment_breakdown(self, days: int = 7) -> list[dict[str, Any]]:
        resp = self._db.db.rpc("payment_breakdown", {"p_days": days}).execute()
        return resp.data or []

    def low_stock(self, limit: int = 20) -> list[dict[str, Any]]:
        resp = self._db.db.rpc("low_stock", {"p_limit": limit}).execute()
        return resp.data or []

    def stock_health(self) -> dict[str, Any]:
        resp = self._db.db.rpc("stock_health").execute()
        data = resp.data or []
        row = data[0] if isinstance(data, list) else data or {}
        return {
            "total_skus": int(row.get("total_skus", 0)),
            "low_stock_skus": int(row.get("low_stock_skus", 0)),
            "out_of_stock_skus": int(row.get("out_of_stock_skus", 0)),
        }

    def sold_items(self, days: int = 1) -> list[dict[str, Any]]:
        resp = self._db.db.rpc("sold_items", {"p_days": days}).execute()
        return resp.data or []

    def money_received(self, days: int = 1) -> list[dict[str, Any]]:
        resp = self._db.db.rpc("money_received", {"p_days": days}).execute()
        return resp.data or []
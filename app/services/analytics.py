from __future__ import annotations

from typing import Any

from ..database.repositories.analytics import AnalyticsRepository


class AnalyticsService:
    """Computes all analytics numbers from Supabase. The AI only ever reads
    and interprets these pre-computed figures — it never calculates them."""

    def __init__(self) -> None:
        self._repo = AnalyticsRepository()

    def sales_summary(self, days: int = 7) -> dict[str, Any]:
        return self._repo.sales_summary(days)

    def daily_sales(self, days: int = 7) -> list[dict[str, Any]]:
        return self._repo.daily_sales(days)

    def top_products(self, days: int = 7, limit: int = 10) -> list[dict[str, Any]]:
        return self._repo.top_products(days, limit)

    def payment_breakdown(self, days: int = 7) -> list[dict[str, Any]]:
        return self._repo.payment_breakdown(days)

    def low_stock(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._repo.low_stock(limit)

    def stock_health(self) -> dict[str, Any]:
        return self._repo.stock_health()

    def sold_items(self, days: int = 1) -> list[dict[str, Any]]:
        return self._repo.sold_items(days)

    def money_received(self, days: int = 1) -> list[dict[str, Any]]:
        return self._repo.money_received(days)

    def snapshot(self, days: int = 7) -> dict[str, Any]:
        """Bundle everything an analysis model needs in one dict."""
        return {
            "sales_summary": self.sales_summary(days),
            "daily_sales": self.daily_sales(days),
            "top_products": self.top_products(days),
            "payment_breakdown": self.payment_breakdown(days),
            "low_stock": self.low_stock(),
            "stock_health": self.stock_health(),
        }
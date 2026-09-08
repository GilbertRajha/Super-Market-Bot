from __future__ import annotations

from typing import Any

from ..services.analytics import AnalyticsService
from .registry import ToolContext


def build(ctx: ToolContext) -> dict[str, dict[str, Any]]:
    service = AnalyticsService()

    def get_daily_sales(days: int = 7) -> list[dict[str, Any]]:
        return service.daily_sales(days)

    def get_sales_summary(days: int = 7) -> dict[str, Any]:
        return service.sales_summary(days)

    def get_top_products(days: int = 7, limit: int = 10) -> list[dict[str, Any]]:
        return service.top_products(days, limit)

    def get_payment_summary(days: int = 7) -> list[dict[str, Any]]:
        return service.payment_breakdown(days)

    def get_stock_health(limit: int = 20) -> dict[str, Any]:
        return {
            "health": service.stock_health(),
            "low_stock": service.low_stock(limit),
        }

    return {
        "get_daily_sales": {
            "description": "Daily finalized-bill totals for the last N days.",
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
            },
            "handler": get_daily_sales,
        },
        "get_sales_summary": {
            "description": "Total sales, GST collected and bill count for a window.",
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
            },
            "handler": get_sales_summary,
        },
        "get_top_products": {
            "description": "Top products by revenue over a window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
            },
            "handler": get_top_products,
        },
        "get_payment_summary": {
            "description": "Sales split by payment method (cash/upi/card/credit).",
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
            },
            "handler": get_payment_summary,
        },
        "get_stock_health": {
            "description": "Stock health: total SKUs, low/out-of-stock items.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
            },
            "handler": get_stock_health,
        },
    }
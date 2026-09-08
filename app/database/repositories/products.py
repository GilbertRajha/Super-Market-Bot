from __future__ import annotations

from typing import Any

from ..supabase import get_db


class ProductRepository:
    """Read + create product data via Supabase REST."""

    TABLE = "products"

    def __init__(self) -> None:
        self._db = get_db()

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        q = (query or "").strip()
        resp = self._db.db.from_(self.TABLE).select("*").ilike("name", f"%{q}%").limit(limit).execute()
        return resp.data or []

    def get(self, product_id: int) -> dict[str, Any] | None:
        resp = (
            self._db.db.from_(self.TABLE)
            .select("*")
            .eq("id", product_id)
            .limit(1)
            .execute()
        )
        data = resp.data or []
        return data[0] if data else None

    def get_by_sku(self, sku: str) -> dict[str, Any] | None:
        resp = (
            self._db.db.from_(self.TABLE)
            .select("*")
            .eq("sku", sku)
            .limit(1)
            .execute()
        )
        data = resp.data or []
        return data[0] if data else None

    def create(
        self,
        sku: str,
        name: str,
        selling_price: float,
        gst_rate: float,
        *,
        category_id: int | None = None,
        unit: str = "piece",
        is_loose: bool = False,
        cost_price: float = 0.0,
        mrp: float | None = None,
        quantity: float = 0.0,
        reorder_level: float = 0.0,
        hsn_code: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "sku": sku,
            "name": name,
            "selling_price": selling_price,
            "gst_rate": gst_rate,
            "unit": unit,
            "is_loose": is_loose,
            "cost_price": cost_price,
            "quantity": quantity,
            "reorder_level": reorder_level,
        }
        if category_id is not None:
            payload["category_id"] = category_id
        if mrp is not None:
            payload["mrp"] = mrp
        if hsn_code:
            payload["hsn_code"] = hsn_code
        resp = self._db.db.from_(self.TABLE).insert(payload).execute()
        return (resp.data or [{}])[0]

    def update(self, product_id: int, fields: dict[str, Any]) -> dict[str, Any]:
        resp = (
            self._db.db.from_(self.TABLE)
            .update(fields)
            .eq("id", product_id)
            .execute()
        )
        return (resp.data or [{}])[0]

    def list_low_stock(self, limit: int = 20) -> list[dict[str, Any]]:
        resp = self._db.db.from_(self.TABLE).select("*").limit(500).execute()
        rows = resp.data or []
        low = [
            row for row in rows
            if float(row.get("quantity", 0) or 0) <= float(row.get("reorder_level", 0) or 0)
        ]
        return low[:limit]

    def all(self, limit: int = 200) -> list[dict[str, Any]]:
        resp = (
            self._db.db.from_(self.TABLE)
            .select("*")
            .order("category_id", desc=False)
            .order("name", desc=False)
            .limit(limit)
            .execute()
        )
        return resp.data or []

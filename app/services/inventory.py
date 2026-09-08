from __future__ import annotations

from typing import Any

from ..database.repositories.products import ProductRepository
from ..database.repositories.stock import StockRepository


class InventoryServiceError(Exception):
    pass


class InventoryService:
    def __init__(self) -> None:
        self._products = ProductRepository()
        self._stock = StockRepository()

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return self._products.search(query, limit=limit)

    def all(self, limit: int = 200) -> list[dict[str, Any]]:
        return self._products.all(limit=limit)

    def get(self, product_id: int) -> dict[str, Any] | None:
        return self._products.get(product_id)

    def create(
        self,
        sku: str,
        name: str,
        selling_price: float,
        gst_rate: float,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self._products.create(sku, name, selling_price, gst_rate, **kwargs)

    def update(self, product_id: int, fields: dict[str, Any]) -> dict[str, Any]:
        return self._products.update(product_id, fields)

    def receive_stock(
        self, product_id: int, qty: float, unit_cost: float | None = None
    ) -> dict[str, Any]:
        if qty <= 0:
            raise InventoryServiceError("quantity must be positive")
        return self._stock.receive_stock(product_id, qty, unit_cost)

    def low_stock(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._products.list_low_stock(limit=limit)

    def stock_movements(
        self, product_id: int | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        return self._stock.movements(product_id=product_id, limit=limit)

    @staticmethod
    def pretty_product(p: dict[str, Any]) -> str:
        return (
            f"#{p['id']} {p['name']} — {p['quantity']} {p.get('unit', 'piece')} "
            f"| sell ₹{float(p['selling_price']):.2f} | GST {float(p.get('gst_rate', 0)):.0f}%"
        )
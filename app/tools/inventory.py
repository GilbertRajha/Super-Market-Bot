from __future__ import annotations

from typing import Any

from ..services.inventory import InventoryService
from .registry import ToolContext


def build(ctx: ToolContext) -> dict[str, dict[str, Any]]:
    service = InventoryService()

    def search_products(query: str, limit: int = 8) -> list[dict[str, Any]]:
        return service.search(query, limit=limit)

    def get_product(product_id: int) -> dict[str, Any] | None:
        return service.get(product_id)

    def get_stock(product_id: int) -> dict[str, Any]:
        product = service.get(product_id)
        if product is None:
            return {"error": "product not found"}
        return {
            "product_id": product["id"],
            "name": product["name"],
            "sku": product["sku"],
            "quantity": float(product["quantity"]),
            "unit": product.get("unit", "piece"),
            "reorder_level": float(product.get("reorder_level", 0)),
        }

    def get_low_stock(limit: int = 15) -> list[dict[str, Any]]:
        return service.low_stock(limit=limit)

    def receive_stock(product_id: int, qty: float, unit_cost: float | None = None) -> dict[str, Any]:
        return service.receive_stock(product_id, qty, unit_cost)

    def create_product(
        sku: str,
        name: str,
        selling_price: float,
        gst_rate: float,
        unit: str = "piece",
        cost_price: float = 0,
        quantity: float = 0,
    ) -> dict[str, Any]:
        return service.create(
            sku, name, selling_price, gst_rate,
            unit=unit, cost_price=cost_price, quantity=quantity,
        )

    def get_stock_movements(product_id: int | None = None, limit: int = 20) -> list[dict[str, Any]]:
        return service.stock_movements(product_id=product_id, limit=limit)

    return {
        "search_products": {
            "description": "Search products by name (fuzzy). Returns id, name, price, gst, quantity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "search text"},
                    "limit": {"type": "integer", "description": "max results"},
                },
                "required": ["query"],
            },
            "handler": search_products,
        },
        "get_product": {
            "description": "Get full details of one product by id.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "integer"}},
                "required": ["product_id"],
            },
            "handler": get_product,
        },
        "get_stock": {
            "description": "Get current stock quantity of a product.",
            "parameters": {
                "type": "object",
                "properties": {"product_id": {"type": "integer"}},
                "required": ["product_id"],
            },
            "handler": get_stock,
        },
        "get_low_stock": {
            "description": "List all products at or below their reorder level.",
            "parameters": {
                "type": "object",
                "properties": {"limit": {"type": "integer"}},
            },
            "handler": get_low_stock,
        },
        "receive_stock": {
            "description": "Add incoming stock to a product. Requires product_id, quantity, optional unit_cost.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer"},
                    "qty": {"type": "number"},
                    "unit_cost": {"type": "number"},
                },
                "required": ["product_id", "qty"],
            },
            "handler": receive_stock,
        },
        "create_product": {
            "description": "Create a new product in inventory. Provide a unique SKU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {"type": "string"},
                    "name": {"type": "string"},
                    "selling_price": {"type": "number"},
                    "gst_rate": {"type": "number"},
                    "unit": {"type": "string"},
                    "cost_price": {"type": "number"},
                    "quantity": {"type": "number"},
                },
                "required": ["sku", "name", "selling_price", "gst_rate"],
            },
            "handler": create_product,
        },
        "get_stock_movements": {
            "description": "Audit trail of stock movements (optionally per product).",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
            },
            "handler": get_stock_movements,
        },
    }
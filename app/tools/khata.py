from __future__ import annotations

from typing import Any

from ..services.khata import KhataService
from .registry import ToolContext


def build(ctx: ToolContext) -> dict[str, dict[str, Any]]:
    service = KhataService()

    def search_customer(query: str, limit: int = 8) -> list[dict[str, Any]]:
        return service.search(query, limit=limit)

    def create_customer(name: str, phone: str | None = None) -> dict[str, Any]:
        return service.create(name, phone)

    def get_credit_balance(customer_id: int) -> dict[str, Any]:
        return {"customer_id": customer_id, "balance": service.balance(customer_id)}

    def record_credit_payment(customer_id: int, amount: float, method: str = "cash") -> dict[str, Any]:
        return service.record_payment(customer_id, amount, method)

    def get_credit_history(customer_id: int, limit: int = 20) -> list[dict[str, Any]]:
        return service.history(customer_id, limit=limit)

    return {
        "search_customer": {
            "description": "Search customers by name (khata ledger).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
            "handler": search_customer,
        },
        "create_customer": {
            "description": "Create a new customer for the khata ledger.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                },
                "required": ["name"],
            },
            "handler": create_customer,
        },
        "get_credit_balance": {
            "description": "Current outstanding credit (khata) balance for a customer.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "integer"}},
                "required": ["customer_id"],
            },
            "handler": get_credit_balance,
        },
        "record_credit_payment": {
            "description": "Record a cash/UPI payment against a customer's khata balance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer"},
                    "amount": {"type": "number"},
                    "method": {"type": "string"},
                },
                "required": ["customer_id", "amount"],
            },
            "handler": record_credit_payment,
        },
        "get_credit_history": {
            "description": "Recent khata transactions for a customer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "integer"},
                    "limit": {"type": "integer"},
                },
                "required": ["customer_id"],
            },
            "handler": get_credit_history,
        },
    }
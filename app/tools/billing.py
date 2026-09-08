from __future__ import annotations

from typing import Any

from ..services.billing import BillingService
from .registry import ToolContext


def build(ctx: ToolContext) -> dict[str, dict[str, Any]]:
    service = BillingService()

    def create_bill() -> dict[str, Any]:
        """Start a new draft bill for this user's open session."""
        return service.start_draft(ctx.telegram_id)

    def get_current_bill() -> dict[str, Any] | None:
        return service.get_current_bill(ctx.telegram_id)

    def add_bill_item(bill_id: int, product_id: int, quantity: float) -> dict[str, Any]:
        return service.add_item(bill_id, product_id, quantity)

    def update_bill_item(bill_id: int, product_id: int, quantity: float) -> dict[str, Any]:
        return service.update_item(bill_id, product_id, quantity)

    def remove_bill_item(bill_id: int, product_id: int) -> dict[str, Any]:
        return service.remove_item(bill_id, product_id)

    def calculate_bill(bill_id: int) -> dict[str, Any]:
        return service.preview(bill_id)

    def set_bill_discount(bill_id: int, amount: float) -> dict[str, Any]:
        return service.set_discount(bill_id, amount)

    def finalize_bill(
        bill_id: int,
        paid: float = 0,
        payment_method: str = "cash",
        idem_key: str | None = None,
    ) -> dict[str, Any]:
        """Finalize a draft bill: validates & decrements stock atomically,
        records payment, and returns the summary. Reduce paid to the total."""
        key = idem_key or f"bill-{bill_id}"
        return service.finalize(
            bill_id,
            ctx.telegram_id,
            paid=paid,
            payment_method=payment_method,
            idem_key=key,
        )

    return {
        "create_bill": {
            "description": "Start a new draft bill (creates an open bill session tied to the user).",
            "parameters": {"type": "object", "properties": {}},
            "handler": create_bill,
        },
        "get_current_bill": {
            "description": "Get the user's current open draft bill, or null.",
            "parameters": {"type": "object", "properties": {}},
            "handler": get_current_bill,
        },
        "add_bill_item": {
            "description": "Add (or increase) a product line on a draft bill. quantity may be fractional for loose items like kg.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bill_id": {"type": "integer"},
                    "product_id": {"type": "integer"},
                    "quantity": {"type": "number"},
                },
                "required": ["bill_id", "product_id", "quantity"],
            },
            "handler": add_bill_item,
        },
        "update_bill_item": {
            "description": "Set a bill line to an exact quantity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bill_id": {"type": "integer"},
                    "product_id": {"type": "integer"},
                    "quantity": {"type": "number"},
                },
                "required": ["bill_id", "product_id", "quantity"],
            },
            "handler": update_bill_item,
        },
        "remove_bill_item": {
            "description": "Remove a product line entirely from a draft bill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bill_id": {"type": "integer"},
                    "product_id": {"type": "integer"},
                },
                "required": ["bill_id", "product_id"],
            },
            "handler": remove_bill_item,
        },
        "calculate_bill": {
            "description": "Compute subtotal, GST breakdown and total for a draft bill.",
            "parameters": {
                "type": "object",
                "properties": {"bill_id": {"type": "integer"}},
                "required": ["bill_id"],
            },
            "handler": calculate_bill,
        },
        "set_bill_discount": {
            "description": "Apply a whole-bill discount in rupees. GST is re-computed on the discounted value.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bill_id": {"type": "integer"},
                    "amount": {"type": "number"},
                },
                "required": ["bill_id", "amount"],
            },
            "handler": set_bill_discount,
        },
        "finalize_bill": {
            "description": "Finalize a draft bill. Decrements stock atomically, records the payment and returns the invoice summary. Use after user confirms and specifies payment method.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bill_id": {"type": "integer"},
                    "paid": {"type": "number", "description": "amount received"},
                    "payment_method": {"type": "string", "description": "cash, upi, card, credit"},
                    "idem_key": {"type": "string", "description": "idempotency key (optional)"},
                },
                "required": ["bill_id"],
            },
            "handler": finalize_bill,
        },
    }
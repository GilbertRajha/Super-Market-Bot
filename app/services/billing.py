from __future__ import annotations

from typing import Any

from ..database.repositories.bills import BillRepository
from ..database.repositories.products import ProductRepository
from .gst import GstLine, GstService
from ..database.repositories.idempotency import IdempotencyRepository


class BillServiceError(Exception):
    """Raised when a billing operation cannot be completed."""


class BillingService:
    """Orchestrates the multi-turn bill lifecycle.

    Drafts are stored as bills with status='draft' tied to a user's open
    session. finalize_bill delegates to the finalize_bill_rpc PostgreSQL
    function which performs stock checks/decrement atomically.
    """

    def __init__(self) -> None:
        self._bills = BillRepository()
        self._products = ProductRepository()
        self._idem = IdempotencyRepository()

    # ---------------------------------------------------------------- draft
    def start_draft(self, telegram_id: int) -> dict[str, Any]:
        session = self._bills.get_or_create_open_session(telegram_id)
        # Reuse the existing open draft instead of creating a duplicate.
        existing = self.get_current_bill(telegram_id)
        if existing is not None:
            return {"session": session, "bill": existing, "reused": True}
        bill = self._bills.insert_bill(session["id"])
        return {"session": session, "bill": bill}

    def get_current_bill(self, telegram_id: int) -> dict[str, Any] | None:
        session = self._bills.get_or_create_open_session(telegram_id)
        # latest draft for this session
        resp = (
            self._bills._db.db.from_("bills")
            .select("*")
            .eq("session_id", session["id"])
            .eq("status", "draft")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        data = resp.data or []
        return data[0] if data else None

    def add_item(self, bill_id: int, product_id: int, quantity: float) -> dict[str, Any]:
        product = self._products.get(product_id)
        if product is None:
            raise BillServiceError("product not found")
        if quantity <= 0:
            raise BillServiceError("quantity must be positive")

        existing = self._bills._db.db.from_("bill_items") \
            .select("*").eq("bill_id", bill_id).eq("product_id", product_id).execute()
        curr = self._bills._db.db.from_("bills").select("*").eq("id", bill_id).limit(1).execute()
        bill = (curr.data or [{}])[0]
        if bill.get("status") == "finalized":
            raise BillServiceError("bill is already finalized")

        existing_rows = existing.data or []
        price = float(product["selling_price"])
        gst_rate = float(product["gst_rate"])

        if existing_rows:
            row = existing_rows[0]
            new_qty = float(row["quantity"]) + quantity
            line_total = round(price * new_qty, 2)
            gst_amount = round(line_total * gst_rate / 100.0, 2)
            self._bills._db.db.from_("bill_items").update({
                "quantity": new_qty, "line_total": line_total, "gst_amount": gst_amount
            }).eq("id", row["id"]).execute()
        else:
            line_total = round(price * quantity, 2)
            gst_amount = round(line_total * gst_rate / 100.0, 2)
            self._bills._db.db.from_("bill_items").insert({
                "bill_id": bill_id,
                "product_id": product_id,
                "product_name": product["name"],
                "unit": product.get("unit", "piece"),
                "quantity": quantity,
                "price": price,
                "gst_rate": gst_rate,
                "gst_amount": gst_amount,
                "line_total": line_total,
            }).execute()

        return self.preview(bill_id)

    def remove_item(self, bill_id: int, product_id: int) -> dict[str, Any]:
        self._bills._db.db.from_("bill_items").delete()\
            .eq("bill_id", bill_id).eq("product_id", product_id).execute()
        return self.preview(bill_id)

    def update_item(self, bill_id: int, product_id: int, quantity: float) -> dict[str, Any]:
        product = self._products.get(product_id)
        if product is None:
            raise BillServiceError("product not found")
        price = float(product["selling_price"])
        gst_rate = float(product["gst_rate"])
        line_total = round(price * quantity, 2)
        gst_amount = round(line_total * gst_rate / 100.0, 2)
        self._bills._db.db.from_("bill_items").update({
            "quantity": quantity, "line_total": line_total, "gst_amount": gst_amount
        }).eq("bill_id", bill_id).eq("product_id", product_id).execute()
        return self.preview(bill_id)

    def set_discount(self, bill_id: int, amount: float) -> dict[str, Any]:
        if amount < 0:
            raise BillServiceError("discount cannot be negative")
        self._bills._db.db.from_("bills").update({"discount": amount}).eq("id", bill_id).execute()
        return self.preview(bill_id)

    def preview(self, bill_id: int) -> dict[str, Any]:
        """Compute a draft preview from stored items via GST logic."""
        items = self._bills.get_items(bill_id)
        gst_lines = [
            GstLine(
                product_name=i["product_name"],
                quantity=float(i["quantity"]),
                price=float(i["price"]),
                gst_rate=float(i["gst_rate"]),
            )
            for i in items
        ]
        gst = GstService.calculate(gst_lines)
        bill = self._bills.get(bill_id) or {}
        discount = float(bill.get("discount", 0) or 0)
        factor = 1.0
        if discount > 0 and gst.subtotal > 0:
            factor = 1.0 - discount / gst.subtotal
        subtotal_after = round(gst.subtotal * factor, 2)
        gst_after = round(gst.gst_amount * factor, 2)
        return {
            "bill_id": bill_id,
            "bill_number": bill.get("bill_number"),
            "items": items,
            "discount": discount,
            "subtotal": subtotal_after,
            "gst_amount": gst_after,
            "total": round(subtotal_after + gst_after, 2),
            "gst_breakdown": gst.breakdown,
        }

    # -------------------------------------------------------------- finalize
    def finalize(
        self,
        bill_id: int,
        telegram_id: int,
        items: list[dict[str, Any]] | None = None,
        paid: float = 0.0,
        payment_method: str = "cash",
        idem_key: str | None = None,
        prefer_cash: bool = False,
    ) -> dict[str, Any]:
        if items is None:
            draft_items = self._bills.get_items(bill_id)
            if not draft_items:
                raise BillServiceError("bill has no items to finalize")
            items = [
                {"product_id": i["product_id"], "quantity": float(i["quantity"])}
                for i in draft_items
            ]

        # idempotency guard: if caller supplies an idem_key, we only finalize once
        if idem_key:
            acquired = self._idem.acquire(telegram_id, "finalize_bill", idem_key, {"bill_id": bill_id})
            if not acquired:
                cached = self._idem.get_result(telegram_id, idem_key)
                if cached:
                    return cached
                raise BillServiceError("duplicate finalize request")

        method = payment_method
        if prefer_cash and method in ("upi", "card"):
            method = "cash"

        try:
            result = self._bills.finalize(
                bill_id, items, paid=paid, payment_method=method
            )
        except Exception as exc:
            if idem_key:
                self._idem._db.db.from_("idempotency_keys").delete()\
                    .eq("telegram_id", telegram_id).eq("idem_key", idem_key).execute()
            raise BillServiceError(str(exc)) from exc

        if idem_key:
            self._idem.store_result(telegram_id, idem_key, result)
        return result
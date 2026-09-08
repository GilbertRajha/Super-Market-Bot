from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GstLine:
    product_name: str
    quantity: float
    price: float
    gst_rate: float


@dataclass
class GstResult:
    subtotal: float
    gst_amount: float
    total: float
    breakdown: dict[float, float]  # gst_rate -> gst_amount


class GstService:
    """Pure GST calculations. The money maths lives here, not in the AI."""

    @staticmethod
    def calculate(items: list[GstLine]) -> GstResult:
        subtotal = 0.0
        gst_amount = 0.0
        breakdown: dict[float, float] = {}

        for item in items:
            line_subtotal = item.quantity * item.price
            line_gst = round(line_subtotal * item.gst_rate / 100.0, 2)
            subtotal += line_subtotal
            gst_amount += line_gst
            breakdown[item.gst_rate] = round(
                breakdown.get(item.gst_rate, 0.0) + line_gst, 2
            )

        return GstResult(
            subtotal=round(subtotal, 2),
            gst_amount=round(gst_amount, 2),
            total=round(subtotal + gst_amount, 2),
            breakdown=breakdown,
        )

    @staticmethod
    def money(value: float) -> str:
        return f"₹{value:,.2f}"
from __future__ import annotations

from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def _money(v: Any) -> str:
    return f"₹{float(v):,.2f}"


def generate_invoice_pdf(bill: dict[str, Any], items: list[dict[str, Any]]) -> bytes:
    """Build a GST invoice PDF for a finalized bill. Returns PDF bytes."""
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ShopTitle", parent=styles["Title"], fontSize=18, spaceAfter=2
    )
    small_style = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9)
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontSize=12, spaceBefore=6, spaceAfter=4
    )

    buf: list[Any] = []
    buf.append(Paragraph("Super Market", title_style))
    buf.append(Paragraph(f"Invoice {bill.get('bill_number', '')}", styles["Normal"]))
    buf.append(
        Paragraph(
            f"Date: {datetime.now():%d %b %Y %I:%M %p}",
            small_style,
        )
    )
    buf.append(Spacer(1, 4 * mm))

    rows = [
        [
            "Item",
            "Unit",
            "Qty",
            "Price",
            "GST%",
            "GST Amt",
            "Line Total",
        ]
    ]
    for i in items:
        rows.append(
            [
                i.get("product_name", ""),
                i.get("unit", "piece"),
                f"{float(i['quantity']):g}",
                _money(i["price"]),
                f"{float(i.get('gst_rate', 0)):.0f}%",
                _money(i.get("gst_amount", 0)),
                _money(i.get("line_total", 0)),
            ]
        )

    table = Table(rows, repeatRows=1, colWidths=[48 * mm, 22 * mm, 15 * mm, 22 * mm, 18 * mm, 22 * mm, 26 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    buf.append(table)
    buf.append(Spacer(1, 4 * mm))

    summary_rows = [
        ["Subtotal", _money(bill.get("subtotal", 0))],
        ["GST", _money(bill.get("gst_amount", 0))],
        ["Total", _money(bill.get("total", 0))],
    ]
    if float(bill.get("discount", 0) or 0) > 0:
        summary_rows.insert(0, ["Gross", _money(float(bill.get("subtotal", 0)) + float(bill.get("discount", 0)))])
        summary_rows.insert(1, ["Discount", "-" + _money(bill.get("discount", 0))])
    summary_rows += [
        ["Payment", bill.get("payment_method", "cash")],
        ["Paid", _money(bill.get("amount_paid", 0))],
        ["Balance due", _money(bill.get("balance_due", 0))],
    ]

    summary = Table(
        summary_rows,
        colWidths=[50 * mm, 40 * mm],
    )
    summary.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOLD", (0, 2), (0, 2)),
                ("BOLD", (0, 4), (0, 4)),
            ]
        )
    )
    buf.append(summary)

    # render to bytes
    from io import BytesIO

    out = BytesIO()
    doc_ = SimpleDocTemplate(
        out,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    doc_.build(buf)
    return out.getvalue()
from __future__ import annotations

import json
from typing import Any

from ..artifacts.invoice import generate_invoice_pdf
from ..artifacts.report import generate_analysis_pptx
from ..database.repositories.bills import BillRepository
from ..services.analytics import AnalyticsService
from .registry import ToolContext


def build(ctx: ToolContext) -> dict[str, dict[str, Any]]:
    bills = BillRepository()
    analytics = AnalyticsService()

    def _queue(artifact: dict[str, Any]) -> None:
        ctx.data.setdefault("artifacts", []).append(artifact)

    def generate_invoice_pdf_tool(bill_id: int) -> dict[str, Any]:
        bill = bills.get(bill_id)
        if bill is None:
            return {"error": "bill not found"}
        items = bills.get_items(bill_id)
        pdf_bytes = generate_invoice_pdf(bill, items)
        filename = f"invoice_{bill.get('bill_number', bill_id)}.pdf"
        _queue({"kind": "pdf", "filename": filename, "data": pdf_bytes})
        return {
            "ok": True,
            "message": f"Invoice {bill.get('bill_number')} generated (total ₹{float(bill.get('total', 0)):.2f}). Sending...",
            "file": filename,
        }

    def generate_analysis_pptx_tool(days: int = 7, insights: str = "") -> dict[str, Any]:
        snapshot = analytics.snapshot(days=days)
        if not insights and ctx.router is not None:
            insights = ctx.router.run_analysis(
                [
                    {
                        "role": "system",
                        "content": (
                            "You are a retail analytics interpreter. Write 3-5 concise, "
                            "insightful bullet points about the sales numbers provided. "
                            "Do NOT invent figures — only talk about what is in the data. "
                            "Use rupee notation like ₹1,234."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Here is the data for the last {days} days:\n{json.dumps(snapshot, ensure_ascii=False, default=str)}",
                    },
                ],
                tools=None,
            ).get("content") or ""
        pptx_bytes = generate_analysis_pptx(snapshot, insights or "See slides.")
        filename = f"weekly_report_{days}d.pptx"
        _queue({"kind": "pptx", "filename": filename, "data": pptx_bytes})
        return {
            "ok": True,
            "message": f"Weekly analytics report generated ({days}d) with AI insights. Sending...",
            "file": filename,
            "insights": insights,
        }

    return {
        "generate_invoice_pdf": {
            "description": "Generate a GST invoice PDF for a finalized (or any) bill. Returns a confirmation; the PDF is sent to the user.",
            "parameters": {
                "type": "object",
                "properties": {"bill_id": {"type": "integer"}},
                "required": ["bill_id"],
            },
            "handler": generate_invoice_pdf_tool,
        },
        "generate_analysis_pptx": {
            "description": "Generate a PPTX sales-analytics report (charts + AI insights) and send it to the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "lookback window in days"},
                    "insights": {"type": "string", "description": "AI-written insights text"},
                },
            },
            "handler": generate_analysis_pptx_tool,
        },
    }
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .router import ModelRouter
from ..tools.registry import Tools

SYSTEM_PROMPT = """You are the assistant of a small Indian supermarket (kirana store), reachable only through Telegram.

You help with:
- Inventory: search products, check / update stock, add incoming stock, low-stock alerts.
- Billing: create draft bills multi-turn, add/update/remove line items, compute GST, then finalize on user confirmation.
- Khata (credit ledger): create customers, record credit sales and payments, show balances.
- Payments: cash / UPI / card / credit.
- Analytics: sales summaries, top products, payment mix, stock health.
- Documents: generate PDF invoices and PPTX sales reports.
- Preferences: remember user defaults (e.g. default payment method) in persistent storage.

HARD RULES
1. NEVER invent numbers, products, stock, balances or sales data. Always use tools to query the database.
2. NEVER give the user raw tool JSON for bill totals when you can summarize lengths cleanly. Show money as ₹1,234.00.
3. Before FINALIZING a bill, ALWAYS present the draft: line items with GST, subtotal, GST amount and total, and ask for confirmation + payment method.
4. Stock safety: if the requested quantity exceeds available stock, DO NOT finalize. Explain available stock and ask for a lower quantity.
5. GST: GST is included via gst_rate per product; compute totals through tools only — do not do your own arithmetic on invoices beyond explaining.
6. Multi-turn: use the ongoing bill session. Do NOT create a new bill every time unless the user asks to start over.
7. Ambiguity: ask one clear, short clarifying question instead of guessing.
8. Keep replies short and friendly; a little Hinglish is fine but be professional. Use bullets for lists.
9. Tools are the ONLY way to touch the database. Never fabricate a tool result.
10. For analytics insight requests, explain the numbers returned by the tools; never re-derive them."""


@dataclass
class AgentResult:
    text: str
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: int = 0


class Agent:
    """Tool-calling agent loop. Uses the router (which hides provider/model
    selection + fallback) and the per-user Tools registry."""

    MAX_ITERS = 6

    def __init__(self, router: ModelRouter, telegram_id: int) -> None:
        self.router = router
        self.tools = Tools(telegram_id)
        self.tools.ctx.router = router

    # ---------------------------------------------------------------- public
    def run(
        self,
        text: str,
        history: list[dict[str, str]] | None = None,
        image_bytes: bytes | None = None,
        image_media_type: str | None = None,
    ) -> AgentResult:
        if image_bytes:
            text = self._run_vision_lane(text, image_bytes, image_media_type)

        messages = self._build_messages(text, history or [])
        tools = self.tools.schemas()
        tool_calls_count = 0

        for _ in range(self.MAX_ITERS):
            response = self.router.run_agent(messages, tools=tools)
            calls = response.get("tool_calls") or []

            if not calls:
                return AgentResult(
                    text=response.get("content") or "Sorry, no response.",
                    artifacts=self.tools.ctx.data.get("artifacts", []),
                    tool_calls=tool_calls_count,
                )

            tool_calls_count += len(calls)
            messages.append(self._assistant_msg(response.get("content"), calls))
            for call in calls:
                result = self.tools.call(call["name"], call["arguments"])
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id"),
                        "name": call["name"],
                        "content": self._serialize(result),
                    }
                )

        return AgentResult(
            text="I could not finish that within the step limit. Please try again.",
            artifacts=self.tools.ctx.data.get("artifacts", []),
            tool_calls=tool_calls_count,
        )

    def _run_vision_lane(self, text: str, image_bytes: bytes, image_media_type: str | None) -> str:
        """Vision role lane: identify the product in the photo, then hand the
        name to the agent lane so it can search Supabase and ask confirmation."""
        try:
            import base64

            data_uri = f"data:{image_media_type or 'image/jpeg'};base64,{base64.b64encode(image_bytes).decode()}"
            response = self.router.run_vision(
                [
                    {
                        "role": "system",
                        "content": (
                            "Identify the single grocery product in the photo. Reply with ONLY the most "
                            "likely product name and a rough size/weight if visible (e.g. 'Tata Salt 1kg'). "
                            "If uncertain, answer 'unknown'."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "What product is this?"},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    },
                ]
            )
            identified = (response.get("content") or "").strip()
            if not identified or identified.lower() == "unknown":
                return text or "The user sent a photo I could not identify.\n"
            return (
                f"{text or ''}\n\nThe user sent a photo. Vision identified it as: \"{identified}\". "
                "Search for a matching product in inventory and ask the user to confirm before using it."
            ).strip()
        except Exception as exc:  # noqa: BLE001
            log = __import__("logging").getLogger(__name__)
            log.warning("Vision lane failed: %s", exc)
            return text

    # -------------------------------------------------------------- rebuild
    def _build_messages(
        self,
        text: str,
        history: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]

        for turn in history:
            messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})

        messages.append({"role": "user", "content": text})
        return messages

    @staticmethod
    def _assistant_msg(content: str | None, calls: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": content or "",
            "tool_calls": [
                {"id": c.get("id"), "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
                for c in calls
            ],
        }

    @staticmethod
    def _serialize(result: Any) -> str:
        import json

        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception:  # noqa: BLE001
            return str(result)

    # ----------------------------------------------------------------- end
    @property
    def artifacts(self) -> list[dict[str, Any]]:
        return self.tools.ctx.data.get("artifacts", [])
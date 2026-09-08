from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from ..ai.agent import Agent
from ..ai.config import settings
from ..ai.conversation import ConversationStore
from ..ai.router import ModelRouter
from ..database.repositories.bills import BillRepository
from ..services.analytics import AnalyticsService
from ..services.billing import BillingService
from ..services.inventory import InventoryService
from .keyboards import quick_keyboard

log = logging.getLogger(__name__)

_agents: dict[int, Agent] = {}
_conv_store = ConversationStore()
_lock = threading.Lock()
_bot_messages: dict[int, list[int]] = {}  # chat_id -> bot message ids (tracked for /new cleanup)


def _money(v: Any) -> str:
    try:
        return f"₹{float(v):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


def _track(chat_id: int, message_id: int | None) -> None:
    if not message_id:
        return
    _bot_messages.setdefault(chat_id, []).append(message_id)
    # keep only the latest 50 so cleanup stays bounded
    _bot_messages[chat_id] = _bot_messages[chat_id][-50:]


def _agent_for(telegram_id: int, router: ModelRouter) -> Agent:
    with _lock:
        if telegram_id not in _agents:
            _agents[telegram_id] = Agent(router, telegram_id)
        return _agents[telegram_id]


async def _reply(update: Update, text: str) -> None:
    msg = await update.message.reply_text(text, reply_markup=quick_keyboard())
    _track(update.effective_chat.id, msg.message_id)


# ------------------------------------------------------------- report builders
def _stock_check_text() -> str:
    inv = InventoryService()
    products = inv.all()
    if not products:
        return "No products in inventory yet."
    lines = ["📦 Current Stock\n" + "-" * 30]
    for p in products:
        name = p.get("name", "")
        qty = float(p.get("quantity", 0) or 0)
        unit = p.get("unit", "piece")
        sell = _money(p.get("selling_price", 0))
        reorder = float(p.get("reorder_level", 0) or 0)
        marker = " ⚠️ LOW" if qty <= reorder else ""
        lines.append(f"{name} — {qty:g} {unit} | {sell}{marker}")
    lines.append("-" * 30)
    lines.append(f"Total SKUs: {len(products)}")
    return "\n".join(lines)


def _low_stock_text() -> str:
    inv = InventoryService()
    low = inv.low_stock(limit=50)
    if not low:
        return "✅ No products are currently low on stock."
    lines = ["📉 Low Stock (qty ≤ reorder level)\n" + "-" * 30]
    for p in low:
        name = p.get("name", "")
        qty = float(p.get("quantity", 0) or 0)
        reorder = float(p.get("reorder_level", 0) or 0)
        unit = p.get("unit", "piece")
        lines.append(f"{name} — {qty:g}/{reorder:g} {unit}")
    lines.append("-" * 30)
    lines.append(f"{len(low)} item(s) low.")
    return "\n".join(lines)


def _today_sales_text() -> str:
    analytics = AnalyticsService()
    summary = analytics.sales_summary(days=1)
    sold = analytics.sold_items(days=1)
    money = analytics.money_received(days=1)
    payments = analytics.payment_breakdown(days=1)

    lines = ["📊 Today's Sales\n" + "-" * 30]
    lines.append(f"Bills finalized: {int(summary.get('bill_count', 0))}")
    lines.append(f"Total sales: {_money(summary.get('total_sales', 0))}")
    lines.append(f"GST collected: {_money(summary.get('gst_collected', 0))}")
    lines.append("")

    lines.append("Stocks delivered today:")
    if sold:
        for s in sold:
            lines.append(f"• {s['product_name']} — {float(s['units_sold']):g} units — {_money(s['revenue'])}")
    else:
        lines.append("• None yet.")

    lines.append("")
    lines.append("Money received:")
    if money:
        by_method: dict[str, float] = {}
        total_received = 0.0
        for m in money:
            by_method[m["method"]] = by_method.get(m["method"], 0.0) + float(m["amount"])
            total_received += float(m["amount"])
        for method, amt in by_method.items():
            lines.append(f"• {method}: {_money(amt)}")
        lines.append(f"Total received: {_money(total_received)}")
    else:
        lines.append("• No money received yet today.")

    lines.append("")
    lines.append("Breakdown by payment method (sales):")
    if payments:
        for p in payments:
            lines.append(f"• {p['method']}: {_money(p['total'])}")
    else:
        lines.append("• None.")
    return "\n".join(lines)


def _weekly_report_text() -> str:
    analytics = AnalyticsService()
    summary = analytics.sales_summary(days=7)
    daily = analytics.daily_sales(days=7)
    top = analytics.top_products(days=7, limit=10)
    payments = analytics.payment_breakdown(days=7)
    low = analytics.low_stock(limit=50)
    health = analytics.stock_health()
    money = analytics.money_received(days=7)
    received_total = sum(float(m.get("amount", 0)) for m in money)

    lines = ["🧾 Weekly Report (last 7 days)\n" + "-" * 30]
    lines.append(f"Bills finalized: {int(summary.get('bill_count', 0))}")
    lines.append(f"Total sales: {_money(summary.get('total_sales', 0))}")
    lines.append(f"GST collected: {_money(summary.get('gst_collected', 0))}")
    lines.append(f"Money received: {_money(received_total)}")
    lines.append("")

    lines.append("Daily sales:")
    if daily:
        for d in daily:
            lines.append(f"• {str(d['day'])[:10]} — {_money(d['total'])} ({int(d['bill_count'])} bills)")
    else:
        lines.append("• No sales.")

    lines.append("")
    lines.append("Top products (by revenue):")
    if top:
        for t in top:
            lines.append(f"• {t['product_name']} — {float(t['units_sold']):g} units — {_money(t['revenue'])}")
    else:
        lines.append("• None.")

    lines.append("")
    lines.append("Payment mix (sales):")
    if payments:
        for p in payments:
            lines.append(f"• {p['method']}: {_money(p['total'])}")
    else:
        lines.append("• None.")

    lines.append("")
    lines.append("Stock health:")
    lines.append(f"• Total SKUs: {health.get('total_skus', 0)}")
    lines.append(f"• Low stock: {health.get('low_stock_skus', 0)}")
    lines.append(f"• Out of stock: {health.get('out_of_stock_skus', 0)}")
    if low:
        lines.append("Low items:")
        for p in low[:10]:
            lines.append(f"  • {p['name']} — {float(p['quantity']):g}/{float(p['reorder_level']):g}")
    lines.append("")
    lines.append("Tip: use the weekly PPTX report via the agent (\"generate weekly report\").")
    return "\n".join(lines)


# ------------------------------------------------------------- button handlers
async def _new_bill(update: Update) -> None:
    user = update.effective_user
    telegram_id = user.id if user else 0
    service = BillingService()
    result = service.start_draft(telegram_id)
    bill = result.get("bill", {})
    if result.get("reused"):
        await _reply(update, f"ℹ️ You already have a draft bill {bill.get('bill_number')} in progress.\n"
                             "Send items like: \"add 6 maggi and 2 atta\"\n"
                             "or /new to cancel and start fresh.")
        return
    await _reply(update, f"🛒 New draft bill {bill.get('bill_number')} created.\n"
                         "Now tell me the items, e.g. \"6 maggi, 2 atta, 1kg sugar\"\n"
                         "or \"add 2 coca cola\".")


async def _stock_check(update: Update) -> None:
    await _reply(update, _stock_check_text())


async def _low_stock(update: Update) -> None:
    await _reply(update, _low_stock_text())


async def _today_sales(update: Update) -> None:
    await _reply(update, _today_sales_text())


async def _weekly_report(update: Update) -> None:
    await _reply(update, _weekly_report_text())


BUTTON_HANDLERS: dict[str, Any] = {
    "🛒 New Bill": _new_bill,
    "📦 Stock Check": _stock_check,
    "📉 Low Stock": _low_stock,
    "📊 Today's Sales": _today_sales,
    "🧾 Weekly Report": _weekly_report,
}

# ---------------------------------------------------------------- agent path
async def _send_artifacts(agent: Agent, update: Update) -> None:
    artifacts = agent.artifacts or []
    agent.tools.ctx.data["artifacts"] = []
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    for art in artifacts:
        data, filename = art.get("data"), art.get("filename")
        if not data:
            continue
        try:
            sent = await update.get_bot().send_document(chat_id, ("artifact", data), filename=filename)
            _track(chat_id, sent.message_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("Failed to send artifact %s: %s", filename, exc)


async def _run_agent(text: str, update: Update, router: ModelRouter, image: bytes | None = None) -> str:
    user = update.effective_user
    telegram_id = user.id if user else 0
    agent = _agent_for(telegram_id, router)
    result = await asyncio.to_thread(
        agent.run,
        text,
        _conv_store.history(telegram_id),
        image,
    )
    _conv_store.add_turn(telegram_id, "user", text)
    _conv_store.add_turn(telegram_id, "assistant", result.text)
    await _send_artifacts(agent, update)
    return result.text


# ---------------------------------------------------------------- commands
async def start(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Namaste! I'm your supermarket ops assistant.\n\n"
        "Use the buttons below to:\n"
        "• New Bill — start a draft bill\n"
        "• Stock Check — current stock\n"
        "• Low Stock — running-low items\n"
        "• Today's Sales — what was sold & money received\n"
        "• Weekly Report — 7-day summary\n\n"
        "You can also type naturally, e.g. \"6 maggi and 2 atta\"\n"
        "/new resets the conversation and clears my messages.",
        reply_markup=quick_keyboard(),
    )


async def new_session(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    telegram_id = user.id if user else 0
    chat_id = update.effective_chat.id

    # reset in-memory conversation + agent
    _conv_store.reset(telegram_id)
    with _lock:
        _agents.pop(telegram_id, None)

    # cancel any open bill session
    try:
        repo = BillRepository()
        session = repo.get_or_create_open_session(telegram_id)
        repo.close_session(session["id"], status="cancelled")
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not close bill session: %s", exc)

    # delete the bot's previous messages in this chat
    deleted = 0
    for mid in list(_bot_messages.pop(chat_id, [])):
        try:
            await update.get_bot().delete_message(chat_id, mid)
            deleted += 1
        except Exception:  # noqa: BLE001
            pass

    await _reply(update, f"✅ Fresh start. Previous {deleted} message(s) cleared.\n"
                         "What do you need?")


# ---------------------------------------------------------------- messages
async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        text = (update.message.text or "").strip()
        router: ModelRouter = ctx.bot_data["router"]

        if text in BUTTON_HANDLERS:
            log.info("Button pressed: %s (chat=%s)", text, update.effective_chat.id)
            await update.message.chat.send_action("typing")
            await BUTTON_HANDLERS[text](update)
            return

        if text in ("🆕 /new", "/new", "new"):
            log.info("/new pressed (chat=%s)", update.effective_chat.id)
            await update.message.chat.send_action("typing")
            await new_session(update, ctx)
            return

        await update.message.chat.send_action("typing")
        reply = await _run_agent(text, update, router)
        await _reply(update, reply)
    except Exception as exc:
        log.exception("on_text failed")
        try:
            await _reply(update, f"⚠️ Sorry, an error occurred. Details: {exc}")
        except Exception:  # noqa: BLE001
            log.exception("Could not send error reply")


async def on_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        telegram_id = user.id if user else 0
        router: ModelRouter = ctx.bot_data["router"]
        agent = _agent_for(telegram_id, router)

        if not settings.VISION_MODEL:
            await _reply(update, "Vision support is not enabled. Configure a VISION_MODEL in .env to identify products from photos.")
            return

        photo = update.message.photo[-1]
        file = await photo.get_file()
        raw = bytes(await file.download_as_bytearray())
        mime = getattr(file, "file_mime_type", None) or "image/jpeg"

        await update.message.chat.send_action("typing")
        caption = update.message.caption or "Identify the product in this photo."
        result = await asyncio.to_thread(
            agent.run,
            caption,
            _conv_store.history(telegram_id),
            raw,
            mime,
        )
        _conv_store.add_turn(telegram_id, "user", caption)
        _conv_store.add_turn(telegram_id, "assistant", result.text)
        await _send_artifacts(agent, update)
        await _reply(update, result.text)
    except Exception as exc:
        log.exception("on_photo failed")
        try:
            await _reply(update, f"⚠️ Sorry, an error occurred processing the photo. Details: {exc}")
        except Exception:  # noqa: BLE001
            log.exception("Could not send error reply")


def build_handlers(router: ModelRouter) -> list[Any]:
    return [
        CommandHandler("start", start),
        CommandHandler("new", new_session),
        CommandHandler("help", start),
        MessageHandler(filters.TEXT & ~filters.COMMAND, on_text),
        MessageHandler(filters.PHOTO, on_photo),
    ]
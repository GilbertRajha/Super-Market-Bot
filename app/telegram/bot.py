from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes

from ..ai.config import settings
from ..ai.router import ModelRouter
from .handlers import build_handlers

log = logging.getLogger(__name__)


async def _error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log any unhandled exception and tell the user (instead of silent no-op)."""
    update_obj = update if isinstance(update, Update) else None
    log.error("Unhandled error: %s", context.error, exc_info=context.error)
    try:
        if update_obj is not None and update_obj.effective_message is not None:
            await update_obj.effective_message.reply_text(
                "⚠️ Sorry, an unexpected error occurred. Please try again."
            )
    except Exception:  # noqa: BLE001
        pass


def create_bot(router: ModelRouter):
    """Build the Telegram Application wired to our handlers."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")

    app = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .concurrent_updates(True)
        .build()
    )
    app.bot_data["router"] = router

    for handler in build_handlers(router):
        app.add_handler(handler)

    app.add_error_handler(_error_handler)
    return app


def run_polling(router: ModelRouter) -> None:
    app = create_bot(router)
    log.info("Starting Telegram polling...")
    app.run_polling(allowed_updates=["message", "edited_message"], drop_pending_updates=True)
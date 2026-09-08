from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup

QUICK: list[list[str]] = [
    ["🛒 New Bill", "📦 Stock Check"],
    ["📉 Low Stock", "📊 Today's Sales"],
    ["🧾 Weekly Report", "🆕 /new"],
]


def quick_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(b) for b in row] for row in QUICK],
        resize_keyboard=True,
    )
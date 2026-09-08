from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Conversation:
    telegram_id: int
    turns: list[dict[str, str]] = field(default_factory=list)
    max_turns: int = 12


class ConversationStore:
    """Bounded in-memory conversation history per user.

    Long-term memory (preferences, defaults) lives in Supabase; this store only
    keeps the recent turns needed for multi-turn billing and follow-ups.
    """

    def __init__(self) -> None:
        self._convs: dict[int, Conversation] = {}

    def get(self, telegram_id: int) -> Conversation:
        if telegram_id not in self._convs:
            self._convs[telegram_id] = Conversation(telegram_id=telegram_id)
        return self._convs[telegram_id]

    def add_turn(self, telegram_id: int, role: str, content: str) -> None:
        conv = self.get(telegram_id)
        conv.turns.append({"role": role, "content": content})
        if len(conv.turns) > conv.max_turns:
            conv.turns = conv.turns[-conv.max_turns :]

    def history(self, telegram_id: int) -> list[dict[str, str]]:
        return self.get(telegram_id).turns

    def reset(self, telegram_id: int) -> None:
        self._convs.pop(telegram_id, None)
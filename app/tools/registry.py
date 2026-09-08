from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from ..ai.providers.base import ToolSchema

log = logging.getLogger(__name__)


@dataclass
class ToolContext:
    """Per-user context injected into tool handlers."""
    telegram_id: int
    session: dict[str, Any] | None = None
    data: dict[str, Any] = field(default_factory=dict)
    router: Any | None = None  # ModelRouter, injected to enable role lanes


class Tools:
    """Registry of tools exposed to the AI agent.

    Tools validate their inputs and call into the service layer — the AI never
    talks to the database directly. The registry is bound to a single user
    (telegram_id) so billing can ride on that user's open draft session.
    """

    def __init__(self, telegram_id: int | None = None) -> None:
        self._tools: dict[str, ToolSchema] = {}
        self.ctx = ToolContext(telegram_id=telegram_id or 0)
        self._register_all()

    # ------------------------------------------------------------ builders
    def _add(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[..., Any],
    ) -> None:
        self._tools[name] = ToolSchema(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
        )

    def _list(self) -> list[ToolSchema]:
        return list(self._tools.values())

    def _register_all(self) -> None:
        from .inventory import build as build_inventory
        from .billing import build as build_billing
        from .khata import build as build_khata
        from .analytics import build as build_analytics
        from .documents import build as build_documents
        from .preferences import build as build_preferences

        for builder in [
            build_inventory,
            build_billing,
            build_khata,
            build_analytics,
            build_documents,
            build_preferences,
        ]:
            specs = builder(self.ctx)
            for name, spec in specs.items():
                self._add(name, spec["description"], spec["parameters"], spec["handler"])

    # ------------------------------------------------------------ dispatch
    def schemas(self) -> list[ToolSchema]:
        return self._list()

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        tool = self._tools.get(name)
        if tool is None:
            return {"error": f"unknown tool: {name}"}
        try:
            log.info("Tool called: %s args=%s", name, arguments)
            result = tool.handler(**arguments)
            if isinstance(result, dict) and "error" in result:
                log.warning("Tool %s returned error: %s", name, result["error"])
            return result
        except Exception as exc:  # noqa: BLE001
            log.exception("Tool %s failed", name)
            return {"error": str(exc)}
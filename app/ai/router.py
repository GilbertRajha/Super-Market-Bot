from __future__ import annotations

import logging

from .providers.base import Provider, ProviderUnavailable, ToolSchema
from .providers.gemini import GeminiProvider
from .providers.openrouter import OpenRouterProvider
from .config import settings

log = logging.getLogger(__name__)


class ModelRouter:
    """Selects and calls the right provider/model for a given *role*.

    Roles are logical lanes (agent, fast, analysis, vision). The router owns
    which concrete provider+model backs each role and handles fallback when
    the primary provider is rate-limited or unavailable.

    The rest of the application calls run_agent/run_fast/run_analysis and does
    not care about the underlying provider.
    """

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}
        self._build_providers()

    # ------------------------------------------------------------- provider
    def _build_providers(self) -> None:
        if settings.OPENROUTER_API_KEY:
            self._providers["openrouter"] = OpenRouterProvider(
                settings.OPENROUTER_API_KEY, settings.PRIMARY_MODEL
            )
        if settings.GEMINI_API_KEY:
            self._providers["gemini"] = GeminiProvider(
                settings.GEMINI_API_KEY, settings.FALLBACK_MODEL
            )
        # A provider must be available.
        if not self._providers:
            raise RuntimeError(
                "No AI provider configured. Set OPENROUTER_API_KEY or GEMINI_API_KEY in .env"
            )

    def _get(self, name: str) -> Provider:
        provider = self._providers.get(name)
        if provider is None:
            # fall back to any provider
            if self._providers:
                return next(iter(self._providers.values()))
            raise RuntimeError("No AI provider configured")
        return provider

    # ---------------------------------------------------------------- util
    def _model_for_role(self, role: str, provider_name: str) -> str | None:
        """Map a role to the configured model for the active provider."""
        if role == "fast":
            return settings.FAST_MODEL or None
        if role == "analysis":
            return settings.ANALYSIS_MODEL or None
        if role == "vision":
            return settings.VISION_MODEL or None
        # agent / default
        if provider_name == "gemini":
            return settings.FALLBACK_MODEL or None
        return settings.PRIMARY_MODEL or None

    def _call(
        self,
        role: str,
        messages: list[dict],
        tools: list[ToolSchema] | None,
        temperature: float | None,
    ) -> dict:
        provider_order = [settings.PRIMARY_PROVIDER, settings.FALLBACK_PROVIDER]
        # de-duplicate, keep configured order, then any remaining providers
        ordered: list[str] = []
        for name in provider_order:
            if name in self._providers and name not in ordered:
                ordered.append(name)
        for name in self._providers:
            if name not in ordered:
                ordered.append(name)

        errors: list[str] = []
        for provider_name in ordered:
            provider = self._get(provider_name)
            model = self._model_for_role(role, provider_name)
            try:
                log.info("Router: role=%s provider=%s model=%s", role, provider_name, model)
                return provider.chat(messages, tools=tools, model=model, temperature=temperature)
            except ProviderUnavailable as exc:
                log.warning("Router: %s failed (%s), trying next", provider_name, exc)
                errors.append(f"{provider_name}: {exc}")
                continue
            except Exception as exc:  # noqa: BLE001
                log.error("Router: %s error (%s)", provider_name, exc)
                errors.append(f"{provider_name}: {exc}")
                # non-unavailability errors bubble up unless we have others left
                if len(ordered) == 1:
                    raise
                continue
        raise RuntimeError(f"All models failed: {'; '.join(errors)}")

    # ------------------------------------------------------------- roles
    def run_agent(
        self,
        messages: list[dict],
        tools: list[ToolSchema] | None = None,
        temperature: float | None = 0.2,
    ) -> dict:
        return self._call("agent", messages, tools, temperature)

    def run_fast(
        self,
        messages: list[dict],
        tools: list[ToolSchema] | None = None,
        temperature: float | None = 0.1,
    ) -> dict:
        return self._call("fast", messages, tools, temperature)

    def run_analysis(
        self,
        messages: list[dict],
        tools: list[ToolSchema] | None = None,
        temperature: float | None = 0.3,
    ) -> dict:
        return self._call("analysis", messages, tools, temperature)

    def run_vision(
        self,
        messages: list[dict],
        tools: list[ToolSchema] | None = None,
        temperature: float | None = 0.1,
    ) -> dict:
        return self._call("vision", messages, tools, temperature)

    # ------------------------------------------------------------ lifecycle
    def close(self) -> None:
        for provider in self._providers.values():
            try:
                provider.close()
            except Exception:  # noqa: BLE001
                pass

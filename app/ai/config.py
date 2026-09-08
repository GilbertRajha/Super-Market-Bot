from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central configuration loaded from .env.

    All AI models are referenced by *role*, not by hard-coded name, so the
    provider/model layer stays replaceable. The router picks a provider and
    a model per role and falls back on failure.
    """

    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    PRIMARY_MODEL: str = os.getenv("PRIMARY_MODEL", "")
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "")
    FAST_MODEL: str = os.getenv("FAST_MODEL", "")
    ANALYSIS_MODEL: str = os.getenv("ANALYSIS_MODEL", "")
    VISION_MODEL: str = os.getenv("VISION_MODEL", "")

    PRIMARY_PROVIDER: str = os.getenv("PRIMARY_PROVIDER", "openrouter")
    FALLBACK_PROVIDER: str = os.getenv("FALLBACK_PROVIDER", "gemini")

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    DATA_DIR: str = os.getenv("DATA_DIR", "data")

    @property
    def log_level(self) -> str:
        return self.LOG_LEVEL.upper()

    @property
    def data_dir(self) -> str:
        return os.path.abspath(self.DATA_DIR)


settings = Settings()

from __future__ import annotations

import logging

from supabase import create_client, Client

from ..ai.config import settings

log = logging.getLogger(__name__)


class Supabase:
    """Single shared Supabase client.

    Simple reads use the client's auto-generated REST API. Critical, atomic,
    concurrency-safe operations (finalize bill, receive stock, khata payment)
    are delegated to PostgreSQL RPC functions.
    """

    def __init__(self) -> None:
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "Supabase is not configured. Set SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY in .env"
            )
        self.client: Client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
        )

    @property
    def db(self) -> Client:
        return self.client


_db: Supabase | None = None


def get_db() -> Supabase:
    global _db
    if _db is None:
        _db = Supabase()
    return _db

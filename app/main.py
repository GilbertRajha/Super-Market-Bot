from __future__ import annotations

import logging

from .ai.config import settings
from .ai.router import ModelRouter
from .telegram.bot import run_polling


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        router = ModelRouter()
    except RuntimeError as exc:
        logging.getLogger(__name__).error("Model router failed to start: %s", exc)
        raise

    from .database.supabase import Supabase

    try:
        Supabase()  # fail fast if Supabase env is missing
    except RuntimeError as exc:
        logging.getLogger(__name__).error("Supabase failed to initialise: %s", exc)
        raise

    run_polling(router)


if __name__ == "__main__":
    main()
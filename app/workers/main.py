# app/workers/main.py

import asyncio
import logging

from aiogram import Bot

from app.core.config import settings
from app.services.meal_checkins import send_due_meal_checkin_requests
from app.services.reminders import send_appointment_24h_reminders
from app.services.privacy import archive_old_meal_report_photo_references
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)


async def run_periodically(name: str, interval_seconds: int, func):
    while True:
        try:
            result = await func()
            logger.info("%s completed: %s", name, result)
        except Exception:
            logger.exception("%s failed", name)

        await asyncio.sleep(interval_seconds)


async def main() -> None:
    setup_logging(debug=False)
    bot = Bot(token=settings.bot_token)

    try:
        await asyncio.gather(
            run_periodically(
                "appointment_reminders",
                600,
                lambda: send_appointment_24h_reminders(bot=bot),
            ),
            run_periodically(
                "meal_checkins",
                60,
                lambda: send_due_meal_checkin_requests(bot=bot),
            ),
            run_periodically(
                "privacy_retention_cleanup",
                86400,
                lambda: archive_old_meal_report_photo_references(older_than_days=180),
            ),
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
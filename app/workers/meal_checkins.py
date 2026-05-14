import asyncio
import logging

from aiogram import Bot

from app.core.config import settings
from app.services.meal_checkins import send_due_meal_checkin_requests

logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(token=settings.bot_token)

    logger.info("Meal checkin worker started")

    try:
        while True:
            result = await send_due_meal_checkin_requests(
                bot=bot,
                lookback_minutes=30,
                limit=50,
            )

            logger.info(
                "Meal checkin worker tick: sent=%s failed=%s skipped=%s",
                result.sent_count,
                result.failed_count,
                result.skipped_count,
            )

            await asyncio.sleep(60)

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
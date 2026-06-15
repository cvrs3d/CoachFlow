import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers import (
    meal_checkins,
    booking,
    client_bookings,
    clients,
    common,
    dashboard,
    language,
    invites,
    meal_reports,
    menu,
    privacy,
    profile,
    registration,
    schedule,
    start,
)
from app.core.config import settings
from app.core.logging import setup_logging
from app.services.bot_commands import setup_default_commands

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging(debug=False)

    logger.info("Starting Bot")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(common.router)

    dp.include_router(start.router)
    dp.include_router(invites.router)
    dp.include_router(dashboard.router)
    dp.include_router(privacy.router)
    dp.include_router(profile.router)
    dp.include_router(registration.router)
    dp.include_router(schedule.router)
    dp.include_router(booking.router)
    dp.include_router(client_bookings.router)
    dp.include_router(clients.router)
    dp.include_router(meal_reports.router)
    dp.include_router(meal_checkins.router)
    dp.include_router(menu.router)
    dp.include_router(language.router)

    await setup_default_commands(bot)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Bot stopped by user")
    except Exception:
        logging.getLogger(__name__).exception("Unhandled application error")
        raise

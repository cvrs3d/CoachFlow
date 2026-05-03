import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.core.config import settings
from app.bot.handlers import start, coach, client, invites, privacy, registration, menu, schedule
from app.services.bot_commands import setup_coach_commands, setup_default_commands
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)

async def main() -> None:
    setup_logging(debug=False)

    logger.info("Starting Bot")

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(privacy.router)
    dp.include_router(invites.router)
    dp.include_router(registration.router)
    dp.include_router(schedule.router)
    dp.include_router(menu.router)

    for coach_telegram_id in settings.coach_ids:
        await setup_coach_commands(bot, coach_telegram_id)

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

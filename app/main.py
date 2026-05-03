import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.core.config import settings
from app.bot.handlers import start, coach, client, invites
from app.services.bot_commands import setup_coach_commands, setup_default_commands

async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(start.router)
    #dp.include_router(coach.router)
    #dp.include_router(client.router)
    dp.include_router(invites.router)

    await setup_default_commands(bot)

    for coach_telegram_id in settings.coach_ids:
        await setup_coach_commands(bot, coach_telegram_id)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

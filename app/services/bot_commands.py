from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)


async def setup_default_commands(bot: Bot) -> None:
    """
    Команды, видимые всем пользователям.
    Здесь НЕ должно быть /invite.
    """
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="health", description="Проверить работу бота"),
        ],
        scope=BotCommandScopeDefault(),
    )


async def setup_coach_commands(bot: Bot, coach_telegram_id: int) -> None:
    """
    Команды, видимые только конкретному тренеру в его чате с ботом.
    """
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="health", description="Проверить работу бота"),
            BotCommand(command="invite", description="Создать ссылку приглашения"),
        ],
        scope=BotCommandScopeChat(chat_id=coach_telegram_id),
    )

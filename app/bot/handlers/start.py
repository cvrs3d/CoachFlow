from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(
        "Привет. Это MVP-бот для тренера.\n\n"
        "Доступные команды:\n"
        "/start\n"
        "/health"
    )


@router.message(Command("health"))
async def health_handler(message: Message) -> None:
    await message.answer("OK")

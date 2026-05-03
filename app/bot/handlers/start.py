from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from app.services.invites import redeem_invite_code

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject) -> None:
    invite_code = command.args

    if not invite_code:
        await message.answer(
            "Привет.\n\n"
            "Для регистрации нужна ссылка приглашения от тренера."
        )
        return

    result = await redeem_invite_code(
        code=invite_code,
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )

    if result.ok:
        await message.answer(
            "Регистрация завершена.\n\n"
            "Теперь вы привязаны к тренеру. "
            "Следующий шаг — добавить меню клиента и Privacy Policy."
        )
        return

    if result.reason == "already_registered":
        await message.answer(
            "Вы уже зарегистрированы."
        )
        return

    if result.reason == "invalid_or_used_invite":
        await message.answer(
            "Ссылка приглашения недействительна, истекла или уже использована. "
            "Попросите тренера создать новую ссылку."
        )
        return

    await message.answer("Не удалось обработать ссылку приглашения.")


@router.message(Command("health"))
async def health_handler(message: Message) -> None:
    await message.answer("OK")


@router.message(Command("myid"))
async def myid_handler(message: Message) -> None:
    await message.answer(f"Ваш Telegram ID: {message.from_user.id}")

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.callbacks.menu import MainMenuCallback
from app.services.users import get_current_user_by_telegram_id

router = Router()


@router.callback_query(MainMenuCallback.filter(F.action == "client_profile"))
async def client_profile_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    current = await get_current_user_by_telegram_id(callback.from_user.id)

    if current is None or current.client is None:
        await callback.message.answer("Профиль клиента не найден.")
        return

    client = current.client
    user = current.user

    text = (
        "👤 Мой профиль\n\n"
        f"Имя для тренера: {client.display_name or 'не указано'}\n"
        f"Цель: {client.goal or 'не указана'}\n"
        f"Статус клиента: {client.status}\n"
        f"Язык интерфейса: {user.language_code}"
    )

    await callback.message.answer(text)
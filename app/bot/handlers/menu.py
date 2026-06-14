from aiogram import Router
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.menu import MainMenuCallback
from app.bot.i18n import get_user_language, t
from app.bot.keyboards.language import language_keyboard
from app.bot.keyboards.main_menu import client_main_menu, coach_main_menu
from app.services.users import get_current_user_by_telegram_id

router = Router()


async def send_main_menu(message: Message, telegram_id: int) -> None:
    current = await get_current_user_by_telegram_id(telegram_id)
    language_code = await get_user_language(telegram_id)

    if current and current.coach and current.user.status == "active":
        await message.answer(
            t("menu.coach.title", language_code),
            reply_markup=coach_main_menu(language_code),
        )
        return

    if current and current.client and current.user.status == "active":
        await message.answer(
            t("menu.client.title", language_code),
            reply_markup=client_main_menu(language_code),
        )
        return

    await message.answer(t("menu.not_registered", language_code))


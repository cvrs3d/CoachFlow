from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.i18n import get_user_language, t
from app.bot.keyboards.language import language_keyboard
from app.bot.keyboards.main_menu import client_main_menu, coach_main_menu
from app.services.language import set_user_language
from app.bot.callbacks.menu import MainMenuCallback

router = Router()


@router.callback_query(MainMenuCallback.filter(F.action == "language"))
async def language_menu_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)

    await callback.answer()

    await callback.message.answer(
        t("language.choose", language_code),
        reply_markup=language_keyboard(),
    )


@router.callback_query(F.data.startswith("lang:set:"))
async def set_language_handler(callback: CallbackQuery) -> None:
    language_code = callback.data.split(":")[-1]

    result = await set_user_language(
        telegram_id=callback.from_user.id,
        language_code=language_code,
    )

    await callback.answer()

    if not result.ok or result.language_code is None:
        await callback.message.answer("Could not update language.")
        return

    if result.role == "coach":
        reply_markup = coach_main_menu(result.language_code)
    else:
        reply_markup = client_main_menu(result.language_code)

    await callback.message.answer(
        t("language.updated", result.language_code),
        reply_markup=reply_markup,
    )
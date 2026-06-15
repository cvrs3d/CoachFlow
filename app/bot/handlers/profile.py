from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.callbacks.menu import MainMenuCallback
from app.bot.i18n import get_user_language, t
from app.services.users import get_current_user_by_telegram_id

router = Router()


@router.callback_query(MainMenuCallback.filter(F.action == "client_profile"))
async def client_profile_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    language_code = await get_user_language(callback.from_user.id)

    current = await get_current_user_by_telegram_id(callback.from_user.id)

    if current is None or current.client is None:
        await callback.message.answer(t("profile.not_found", language_code))
        return

    client = current.client
    user = current.user
    display_name = client.display_name or t("profile.display_name_unknown", language_code)
    goal = client.goal or t("profile.goal_unknown", language_code)
    status_label = t(f"client_status.{client.status}", language_code)

    text = (
        t("profile.title", language_code)
        + "\n\n"
        + t("profile.name", language_code, display_name=display_name)
        + "\n"
        + t("profile.goal", language_code, goal=goal)
        + "\n"
        + t("profile.status", language_code, status=status_label)
        + "\n"
        + t("profile.language", language_code, interface_language=user.language_code)
    )

    await callback.message.answer(text)
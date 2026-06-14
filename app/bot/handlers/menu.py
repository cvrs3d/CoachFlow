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


@router.callback_query(MainMenuCallback.filter())
async def main_menu_action_handler(
    callback: CallbackQuery,
    callback_data: MainMenuCallback,
) -> None:
    action = callback_data.action

    await callback.answer()

    # Здесь только диспетчеризация.
    # Вариант 1: вызывать service напрямую здесь.
    # Вариант 2: оставить callback handlers в профильных файлах.

# @router.message(F.text == "🔗 Создать приглашение")
# async def create_invite_button_handler(message: Message) -> None:
#     coach = await get_coach_by_telegram_id(message.from_user.id)

#     if coach is None:
#         return

#     invite = await create_invite_for_coach(
#         coach_id=coach.id,
#         max_uses=1,
#         expires_in_days=7,
#     )

#     bot_user = await message.bot.get_me()
#     link = f"https://t.me/{bot_user.username}?start={invite.code}"

#     await message.answer(
#         f"Ссылка приглашения создана.\n\n{link}\n\nСсылка одноразовая и действует 7 дней."
#     )


# @router.message(F.text == "👤 Мой профиль")
# async def client_profile_handler(message: Message) -> None:
#     current = await get_current_user_by_telegram_id(message.from_user.id)

#     if not current or not current.client or current.user.status != "active":
#         return

#     await message.answer(
#         "Ваш профиль:\n\n"
#         f"Имя: {current.client.display_name or 'не указано'}\n"
#         f"Статус: {current.client.status}"
#     )

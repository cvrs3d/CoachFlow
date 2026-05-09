from aiogram import F, Router
from aiogram.types import Message

from app.services.invites import create_invite_for_coach, get_coach_by_telegram_id
from app.services.users import get_current_user_by_telegram_id

router = Router()


@router.message(F.text == "🔗 Создать приглашение")
async def create_invite_button_handler(message: Message) -> None:
    coach = await get_coach_by_telegram_id(message.from_user.id)

    if coach is None:
        return

    invite = await create_invite_for_coach(
        coach_id=coach.id,
        max_uses=1,
        expires_in_days=7,
    )

    bot_user = await message.bot.get_me()
    link = f"https://t.me/{bot_user.username}?start={invite.code}"

    await message.answer(
        "Ссылка приглашения создана.\n\n"
        f"{link}\n\n"
        "Ссылка одноразовая и действует 7 дней."
    )


@router.message(F.text == "👤 Мой профиль")
async def client_profile_handler(message: Message) -> None:
    current = await get_current_user_by_telegram_id(message.from_user.id)

    if not current or not current.client or current.user.status != "active":
        return

    await message.answer(
        "Ваш профиль:\n\n"
        f"Имя: {current.client.display_name or 'не указано'}\n"
        f"Статус: {current.client.status}"
    )
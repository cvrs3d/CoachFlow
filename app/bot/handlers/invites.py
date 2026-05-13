from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.invites import create_invite_for_coach, get_coach_by_telegram_id

router = Router()


@router.message(Command("invite"))
async def create_invite_handler(message: Message) -> None:
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
        f"Ссылка приглашения создана.\n\n{link}\n\nСсылка одноразовая и действует 7 дней."
    )

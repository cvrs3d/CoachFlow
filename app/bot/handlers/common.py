from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.common import CommonCallback
from app.bot.i18n import get_user_language, t

router = Router()


async def _cancel_state(
    *,
    telegram_id: int,
    state: FSMContext,
) -> tuple[bool, str]:
    language_code = await get_user_language(telegram_id)
    current_state = await state.get_state()

    if current_state is None:
        return False, t("common.no_active_action", language_code)

    await state.clear()
    return True, t("common.action_cancelled", language_code)


@router.message(Command("cancel"))
async def cancel_command_handler(
    message: Message,
    state: FSMContext,
) -> None:
    _, text = await _cancel_state(
        telegram_id=message.from_user.id,
        state=state,
    )
    await message.answer(text)


@router.callback_query(CommonCallback.filter(F.action == "cancel"))
async def cancel_callback_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    _, text = await _cancel_state(
        telegram_id=callback.from_user.id,
        state=state,
    )

    await callback.answer()
    await callback.message.answer(text)

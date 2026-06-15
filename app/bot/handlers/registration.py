from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.i18n import get_user_language, t
from app.bot.keyboards.common import cancel_keyboard
from app.bot.keyboards.privacy import privacy_consent_keyboard
from app.bot.states.registration import RegistrationStates
from app.services.users import set_client_display_name

router = Router()


@router.message(RegistrationStates.waiting_for_display_name)
async def process_display_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    language_code = await get_user_language(message.from_user.id)
    display_name = (message.text or "").strip()

    if len(display_name) < 2:
        await message.answer(
            t("registration.name_too_short", language_code),
            reply_markup=cancel_keyboard(language_code),
        )
        return

    if len(display_name) > 80:
        await message.answer(
            t("registration.name_too_long", language_code),
            reply_markup=cancel_keyboard(language_code),
        )
        return

    ok = await set_client_display_name(
        telegram_id=message.from_user.id,
        display_name=display_name,
    )

    if not ok:
        await state.clear()
        await message.answer(t("registration.save_failed", language_code))
        return

    await state.clear()

    await message.answer(
        t("registration.saved", language_code)
        + "\n\n"
        + t("registration.consent_needed", language_code)
        + "\n\n"
        + t("registration.consent_text", language_code)
        + "\n\n"
        + t("registration.consent_item.telegram_id", language_code)
        + "\n"
        + t("registration.consent_item.display_name", language_code)
        + "\n"
        + t("registration.consent_item.bookings", language_code)
        + "\n"
        + t("registration.consent_item.history", language_code)
        + "\n\n"
        + t("registration.consent_footer", language_code),
        reply_markup=privacy_consent_keyboard(language_code),
    )

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.i18n import get_user_language, t
from app.bot.keyboards.common import cancel_keyboard
from app.bot.keyboards.main_menu import client_main_menu, coach_main_menu
from app.bot.keyboards.privacy import privacy_consent_keyboard
from app.bot.states.registration import RegistrationStates
from app.services.invites import redeem_invite_code
from app.services.users import get_current_user_by_telegram_id

router = Router()


@router.message(CommandStart())
async def start_handler(
    message: Message,
    command: CommandObject,
    state: FSMContext,
) -> None:
    current = await get_current_user_by_telegram_id(message.from_user.id)
    language_code = await get_user_language(message.from_user.id)

    # 1. Trainer panel
    if current and current.coach and current.user.status == "active":
        await message.answer(
            t("menu.coach.title", language_code),
            reply_markup=coach_main_menu(language_code),
        )
        return

    # 2. Active clients panel
    if current and current.client and current.user.status == "active":
        await message.answer(
            t("menu.client.title", language_code),
            reply_markup=client_main_menu(language_code),
        )
        return

    # 3. Pending клиент без нового invite — повторно показываем consent
    if current and current.client and current.user.status == "pending":
        if not current.client.display_name:
            await state.set_state(RegistrationStates.waiting_for_display_name)
            await message.answer(
                t("start.registration_started", language_code),
                reply_markup=cancel_keyboard(language_code),
            )
            return

        await message.answer(
            t("start.consent_needed", language_code)
            + "\n\n"
            + t("start.consent_text", language_code)
            + "\n\n"
            + t("start.consent_summary", language_code)
            + "\n"
            + "- Telegram ID;\n"
            + "- имя, указанное для тренера;\n"
            + "- записи к тренеру;\n"
            + "- отчеты еды и Telegram file_id фото;\n"
            + "- статусы проверок и комментарии тренера.\n\n"
            + t("start.consent_privacy_link", language_code),
            reply_markup=privacy_consent_keyboard(language_code),
        )
        return

    invite_code = command.args

    # 4. Незарегистрированный пользователь без invite
    if not invite_code:
        await message.answer(t("start.registration_link_required", language_code))
        return

    # 5. Новый пользователь с invite
    result = await redeem_invite_code(
        code=invite_code, telegram_id=message.from_user.id, username=message.from_user.username
    )

    if result.ok:
        await state.set_state(RegistrationStates.waiting_for_display_name)

        await message.answer(
            t("start.invite_confirmed", language_code)
            + "\n\n"
            + t("start.name_prompt", language_code)
            + "\n\n"
            + t("start.name_example", language_code),
            reply_markup=cancel_keyboard(language_code),
        )
        return

    if result.reason == "already_registered":
        await message.answer(t("start.already_registered", language_code))
        return

    if result.reason == "pending_consent":
        await message.answer(
            t("start.pending_consent", language_code),
            reply_markup=privacy_consent_keyboard(language_code),
        )
        return

    if result.reason == "invalid_or_used_invite":
        await message.answer(t("start.invalid_invite", language_code))
        return

    await message.answer(t("start.processing_failed", language_code))


@router.message(Command("health"))
async def health_handler(message: Message) -> None:
    await message.answer("OK")


@router.message(Command("myid"))
async def myid_handler(message: Message) -> None:
    await message.answer(f"Ваш Telegram ID: {message.from_user.id}")

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.main_menu import client_main_menu, coach_main_menu
from app.bot.keyboards.privacy import privacy_consent_keyboard
from app.bot.states.registration import RegistrationStates
from app.services.invites import redeem_invite_code
from app.services.users import get_current_user_by_telegram_id
from app.bot.i18n import get_user_language, t

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
            await message.answer("Регистрация уже начата.\n\nКак вас записать для тренера?")
            return

        await message.answer(
            "Для завершения регистрации нужно согласие на обработку данных.\n\n"
            "Нажимая “Согласен”, вы подтверждаете, что ознакомились с политикой обработки данных.\n\n"
            "Кратко бот хранит:\n"
            "- Telegram ID;\n"
            "- имя, указанное для тренера;\n"
            "- записи к тренеру;\n"
            "- отчеты еды и Telegram file_id фото;\n"
            "- статусы проверок и комментарии тренера.\n\n"
            "Полный текст: /privacy",
            reply_markup=privacy_consent_keyboard(),
        )
        return

    invite_code = command.args

    # 4. Незарегистрированный пользователь без invite
    if not invite_code:
        await message.answer("Для регистрации нужна ссылка приглашения от тренера.")
        return

    # 5. Новый пользователь с invite
    result = await redeem_invite_code(
        code=invite_code, telegram_id=message.from_user.id, username=message.from_user.username
    )

    if result.ok:
        await state.set_state(RegistrationStates.waiting_for_display_name)

        await message.answer(
            "Ссылка приглашения подтверждена.\n\n"
            "Как вас записать для тренера?\n\n"
            "Введите имя, которое будет видно тренеру. Например: Алексей."
        )
        return

    if result.reason == "already_registered":
        await message.answer("Вы уже зарегистрированы.")
        return

    if result.reason == "pending_consent":
        await message.answer(
            "Регистрация уже начата.\n\nДля завершения нужно согласие на обработку данных.",
            reply_markup=privacy_consent_keyboard(),
        )
        return

    if result.reason == "invalid_or_used_invite":
        await message.answer(
            "Ссылка приглашения недействительна, истекла или уже использована. "
            "Попросите тренера создать новую ссылку."
        )
        return

    await message.answer("Не удалось обработать ссылку приглашения.")


@router.message(Command("health"))
async def health_handler(message: Message) -> None:
    await message.answer("OK")


@router.message(Command("myid"))
async def myid_handler(message: Message) -> None:
    await message.answer(f"Ваш Telegram ID: {message.from_user.id}")

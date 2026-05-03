from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import Message

from app.bot.keyboards.privacy import privacy_consent_keyboard
from app.services.invites import redeem_invite_code
from app.services.users import get_current_user_by_telegram_id

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, command: CommandObject) -> None:
    current = await get_current_user_by_telegram_id(message.from_user.id)

    # 1. Тренер без invite не должен видеть "нужна ссылка от тренера"
    if current and current.coach and current.user.status == "active":
        await message.answer(
            "Панель тренера.\n\n"
            "Доступные команды:\n"
            "/invite — создать ссылку приглашения\n"
            "/health — проверить работу бота"
        )
        return

    # 2. Уже активный клиент
    if current and current.client and current.user.status == "active":
        await message.answer(
            "Вы уже зарегистрированы.\n\n"
            "Скоро здесь будет меню клиента."
        )
        return

    # 3. Pending клиент без нового invite — повторно показываем consent
    if current and current.client and current.user.status == "pending":
        await message.answer(
            "Для завершения регистрации нужно согласие на обработку данных.\n\n"
            "Мы будем обрабатывать ваш Telegram ID, имя, записи к тренеру, "
            "сообщения и фото еды, которые вы отправляете в бот.\n\n"
            "Данные используются только для работы сервиса тренера.",
            reply_markup=privacy_consent_keyboard(),
        )
        return

    invite_code = command.args

    # 4. Незарегистрированный пользователь без invite
    if not invite_code:
        await message.answer(
            "Для регистрации нужна ссылка приглашения от тренера."
        )
        return

    # 5. Новый пользователь с invite
    result = await redeem_invite_code(
        code=invite_code,
        telegram_id=message.from_user.id,
        username=message.from_user.username
    )

    if result.ok:
        await message.answer(
            "Ссылка приглашения подтверждена.\n\n"
            "Для завершения регистрации нужно согласие на обработку данных.\n\n"
            "Мы будем обрабатывать ваш Telegram ID, имя, записи к тренеру, "
            "сообщения и фото еды, которые вы отправляете в бот.\n\n"
            "Данные используются только для работы сервиса тренера.",
            reply_markup=privacy_consent_keyboard(),
        )
        return

    if result.reason == "already_registered":
        await message.answer("Вы уже зарегистрированы.")
        return
    
    if result.reason == "pending_consent":
        await message.answer(
            "Регистрация уже начата.\n\n"
            "Для завершения нужно согласие на обработку данных.",
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

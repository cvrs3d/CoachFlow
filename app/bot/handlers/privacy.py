from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command

from app.bot.keyboards.main_menu import client_main_menu
from app.bot.texts.privacy import PRIVACY_POLICY_TEXT
from app.services.users import activate_user_after_consent
from app.services.privacy import export_user_data
from aiogram.types import BufferedInputFile

router = Router()


@router.message(Command("export_my_data"))
async def export_my_data_command_handler(message: Message) -> None:
    result = await export_user_data(telegram_id=message.from_user.id)

    if not result.ok or result.file_bytes is None or result.filename is None:
        await message.answer("Не удалось подготовить экспорт данных.")
        return

    await message.answer_document(
        BufferedInputFile(
            result.file_bytes,
            filename=result.filename,
        ),
        caption="Ваш экспорт данных CoachFlow.",
    )

@router.message(Command("privacy"))
async def privacy_command_handler(message: Message) -> None:
    await message.answer(PRIVACY_POLICY_TEXT)

@router.callback_query(F.data == "privacy:accept")
async def accept_privacy_handler(callback: CallbackQuery) -> None:
    ok = await activate_user_after_consent(callback.from_user.id)

    await callback.answer()

    if not ok:
        await callback.message.answer(
            "Не удалось активировать профиль. Попросите тренера отправить новую ссылку."
        )
        return

    await callback.message.edit_text(
        "Регистрация завершена.\n\nТеперь вы можете пользоваться ботом."
    )

    await callback.message.answer(
        "Главное меню клиента:",
        reply_markup=client_main_menu(),
    )


@router.callback_query(F.data == "privacy:decline")
async def decline_privacy_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    await callback.message.edit_text(
        "Регистрация не завершена.\n\nБез согласия на обработку данных бот не может использоваться."
    )

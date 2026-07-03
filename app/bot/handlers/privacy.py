from aiogram import F, Router
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.filters import Command

from app.bot.keyboards.main_menu import client_main_menu
from app.bot.i18n import get_user_language, t
from app.bot.texts.privacy import PRIVACY_POLICY_TEXT
from app.services.users import activate_user_after_consent
from aiogram.types import BufferedInputFile
from app.bot.keyboards.privacy import delete_my_data_confirm_keyboard
from app.services.privacy import export_user_data, request_data_deletion

router = Router()

@router.message(Command("delete_my_data"))
async def delete_my_data_command_handler(message: Message) -> None:
    language_code = await get_user_language(message.from_user.id)
    await message.answer(
        t("privacy.delete_intro", language_code),
        reply_markup=delete_my_data_confirm_keyboard(),
    )


@router.callback_query(F.data == "privacy:delete_confirm")
async def confirm_delete_my_data_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    result = await request_data_deletion(telegram_id=callback.from_user.id)

    await callback.answer()

    if not result.ok:
        await callback.message.edit_text(
            t("privacy.delete_failed", language_code)
        )
        return

    if result.reason == "already_pending":
        await callback.message.edit_text(
            t("privacy.delete_pending", language_code)
        )
        return

    await callback.message.edit_text(
        t("privacy.delete_created", language_code)
    )


@router.callback_query(F.data == "privacy:delete_cancel")
async def cancel_delete_my_data_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    await callback.answer()
    await callback.message.edit_text(t("privacy.delete_cancelled", language_code))

@router.message(Command("export_my_data"))
async def export_my_data_command_handler(message: Message) -> None:
    language_code = await get_user_language(message.from_user.id)
    result = await export_user_data(telegram_id=message.from_user.id)

    if not result.ok or result.file_bytes is None or result.filename is None:
        await message.answer(t("privacy.export_failed", language_code))
        return

    await message.answer_document(
        BufferedInputFile(
            result.file_bytes,
            filename=result.filename,
        ),
        caption=t("privacy.export_caption", language_code),
    )

@router.message(Command("privacy"))
async def privacy_command_handler(message: Message) -> None:
    language_code = await get_user_language(message.from_user.id)
    await message.answer(PRIVACY_POLICY_TEXT)

@router.callback_query(F.data == "privacy:accept")
async def accept_privacy_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    ok = await activate_user_after_consent(callback.from_user.id)

    await callback.answer()

    if not ok:
        await callback.message.answer(
            t("privacy.activate_failed", language_code)
        )
        return

    await callback.message.edit_text(
        t("privacy.registered", language_code)
    )

    await callback.message.answer(
        t("common.reply_keyboard_removed", language_code),
        reply_markup=ReplyKeyboardRemove(),
    )

    await callback.message.answer(
        t("privacy.client_menu", language_code),
        reply_markup=client_main_menu(language_code),
    )

@router.callback_query(F.data == "privacy:decline")
async def decline_privacy_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    await callback.answer()

    await callback.message.edit_text(
        t("privacy.registration_incomplete", language_code)
    )

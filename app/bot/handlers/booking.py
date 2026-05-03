from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.booking import available_slots_keyboard
from app.services.booking import (
    book_slot_for_client,
    list_available_slots_for_client,
)

router = Router()


@router.message(F.text == "📅 Выбрать время")
async def choose_time_handler(message: Message) -> None:
    slots = await list_available_slots_for_client(
        telegram_id=message.from_user.id,
        limit=10,
    )

    if not slots:
        await message.answer(
            "Сейчас нет доступных слотов для записи."
        )
        return

    await message.answer(
        "Выберите доступное время:",
        reply_markup=available_slots_keyboard(slots),
    )


@router.callback_query(F.data.startswith("book_slot:"))
async def book_slot_handler(callback: CallbackQuery) -> None:
    slot_id = callback.data.split(":", 1)[1]

    result = await book_slot_for_client(
        telegram_id=callback.from_user.id,
        slot_id=slot_id,
    )

    await callback.answer()

    if result.ok:
        await callback.message.edit_text(
            "Запись подтверждена.\n\n"
            f"Время: {result.starts_at} — {result.ends_at}"
        )
        return

    if result.reason == "slot_not_available":
        await callback.message.edit_text(
            "Это время уже занято. Выберите другой слот."
        )
        return

    if result.reason == "client_not_found":
        await callback.message.edit_text(
            "Не удалось найти активный профиль клиента."
        )
        return

    await callback.message.edit_text(
        "Не удалось забронировать слот."
    )
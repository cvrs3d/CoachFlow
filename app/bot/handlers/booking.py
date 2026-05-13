from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.booking import available_slots_keyboard
from app.services.booking import (
    book_slot_for_client,
    get_active_client_context,
    list_available_slots_for_client,
)
from app.services.notifications import send_logged_message
from app.utils.datetime import format_slot_range_for_timezone

router = Router()


@router.message(F.text == "📅 Выбрать время")
async def choose_time_handler(message: Message) -> None:
    context = await get_active_client_context(message.from_user.id)

    if context is None:
        await message.answer("Не удалось найти активный профиль клиента.")
        return

    slots = await list_available_slots_for_client(
        telegram_id=message.from_user.id,
        limit=10,
    )

    if not slots:
        await message.answer("Сейчас нет доступных слотов для записи.")
        return

    await message.answer(
        f"Выберите доступное время.\nВремя указано в часовом поясе тренера: {context.coach.timezone}",
        reply_markup=available_slots_keyboard(slots, context.coach.timezone),
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
        context = await get_active_client_context(callback.from_user.id)
        timezone_name = context.coach.timezone if context else "Europe/Prague"

        # если result.starts_at/result.ends_at строки:
        from datetime import datetime

        starts_at = (
            datetime.fromisoformat(result.starts_at)
            if isinstance(result.starts_at, str)
            else result.starts_at
        )
        ends_at = (
            datetime.fromisoformat(result.ends_at)
            if isinstance(result.ends_at, str)
            else result.ends_at
        )

        slot_time = format_slot_range_for_timezone(
            starts_at,
            ends_at,
            timezone_name,
        )

        await callback.message.edit_text(
            f"Запись подтверждена.\n\nВремя: {slot_time}\nЧасовой пояс: {timezone_name}"
        )

        if result.coach_telegram_id is not None:
            await send_logged_message(
                bot=callback.bot,
                chat_id=result.coach_telegram_id,
                notification_type="appointment_booked",
                related_entity_type="appointment",
                related_entity_id=result.appointment_id,
                text=(
                    "Новая запись.\n\n"
                    f"Клиент: {result.client_display_name or 'без имени'}\n"
                    f"Время: {slot_time}\n"
                    f"Часовой пояс: {timezone_name}"
                ),
            )

        return

    if result.reason == "slot_not_available":
        await callback.message.edit_text("Это время уже занято. Выберите другой слот.")
        return

    if result.reason == "client_not_found":
        await callback.message.edit_text("Не удалось найти активный профиль клиента.")
        return

    await callback.message.edit_text("Не удалось забронировать слот.")

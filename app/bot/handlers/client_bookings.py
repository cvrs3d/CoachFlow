from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from app.bot.callbacks.menu import MainMenuCallback

from app.bot.keyboards.client_bookings import (
    client_booking_card_keyboard,
    client_bookings_keyboard,
    confirm_cancel_client_booking_keyboard,
)
from app.services.client_bookings import (
    cancel_booking_by_client,
    get_active_client_context,
    get_client_booking_card,
    list_future_bookings_for_client,
)
from app.services.notifications import send_logged_message
from app.utils.datetime import format_slot_range_for_timezone

router = Router()


@router.callback_query(MainMenuCallback.filter(F.action == "client_bookings"))
async def my_bookings_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    context = await get_active_client_context(callback.from_user.id)

    if context is None:
        await callback.message.answer("Не удалось найти активный профиль клиента.")
        return

    bookings = await list_future_bookings_for_client(
        telegram_id=callback.from_user.id,
        limit=10,
    )

    if not bookings:
        await callback.message.answer("У вас нет будущих записей.")
        return

    await callback.message.answer(
        f"Ваши будущие записи.\nВремя указано в часовом поясе тренера: {context.coach.timezone}",
        reply_markup=client_bookings_keyboard(bookings, context.coach.timezone),
    )   


@router.callback_query(F.data == "c_b:l")
async def my_bookings_callback_handler(callback: CallbackQuery) -> None:
    context = await get_active_client_context(callback.from_user.id)

    await callback.answer()

    if context is None:
        await callback.message.edit_text("Не удалось найти активный профиль клиента.")
        return

    bookings = await list_future_bookings_for_client(
        telegram_id=callback.from_user.id,
        limit=10,
    )

    if not bookings:
        await callback.message.edit_text("У вас нет будущих записей.")
        return

    await callback.message.edit_text(
        f"Ваши будущие записи.\nВремя указано в часовом поясе тренера: {context.coach.timezone}",
        reply_markup=client_bookings_keyboard(bookings, context.coach.timezone),
    )


@router.callback_query(F.data.startswith("c_b:o"))
async def open_client_booking_handler(callback: CallbackQuery) -> None:
    appointment_id = callback.data.split(":", 2)[2]

    card = await get_client_booking_card(
        telegram_id=callback.from_user.id,
        appointment_id=appointment_id,
    )

    await callback.answer()

    if card is None:
        await callback.message.edit_text("Запись не найдена или уже отменена.")
        return

    slot_time = format_slot_range_for_timezone(
        card.slot.starts_at,
        card.slot.ends_at,
        card.coach.timezone,
    )

    if card.can_cancel:
        cancel_text = (
            f"Отмена доступна: да\n"
            f"Правило отмены: не позднее чем за {card.cancellation_deadline_hours} ч."
        )
    else:
        cancel_text = (
            "Отмена через бот уже недоступна.\n"
            f"Правило отмены: не позднее чем за {card.cancellation_deadline_hours} ч.\n"
            "Свяжитесь с тренером напрямую."
        )

    text = (
        "Карточка записи\n\n"
        f"Время: {slot_time}\n"
        f"Часовой пояс: {card.coach.timezone}\n"
        f"Статус: {card.appointment.status}\n\n"
        f"{cancel_text}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=client_booking_card_keyboard(
            appointment_id=card.appointment.id,
            can_cancel=card.can_cancel,
        ),
    )


@router.callback_query(F.data.startswith("c_b:c_c:"))
async def confirm_cancel_client_booking_handler(callback: CallbackQuery) -> None:
    appointment_id = callback.data.split(":", 2)[2]

    card = await get_client_booking_card(
        telegram_id=callback.from_user.id,
        appointment_id=appointment_id,
    )

    await callback.answer()

    if card is None:
        await callback.message.edit_text("Запись не найдена или уже отменена.")
        return

    if not card.can_cancel:
        await callback.message.edit_text(
            "Отмена через бот уже недоступна. Свяжитесь с тренером напрямую."
        )
        return

    slot_time = format_slot_range_for_timezone(
        card.slot.starts_at,
        card.slot.ends_at,
        card.coach.timezone,
    )

    await callback.message.edit_text(
        "Отменить запись?\n\n"
        f"Время: {slot_time}\n"
        f"Часовой пояс: {card.coach.timezone}\n\n"
        "После отмены слот снова станет доступен другим клиентам.",
        reply_markup=confirm_cancel_client_booking_keyboard(appointment_id),
    )


@router.callback_query(F.data.startswith("c_b:c:"))
async def cancel_client_booking_handler(callback: CallbackQuery) -> None:
    appointment_id = callback.data.split(":", 2)[2]

    result = await cancel_booking_by_client(
        telegram_id=callback.from_user.id,
        appointment_id=appointment_id,
    )

    await callback.answer()

    if not result.ok:
        if result.reason == "too_late":
            await callback.message.edit_text(
                "Отмена через бот уже недоступна. Свяжитесь с тренером напрямую."
            )
            return

        await callback.message.edit_text("Не удалось отменить запись. Возможно, она уже отменена.")
        return

    context = await get_active_client_context(callback.from_user.id)
    timezone_name = context.coach.timezone if context else "Europe/Prague"

    slot_time = format_slot_range_for_timezone(
        result.starts_at,
        result.ends_at,
        timezone_name,
    )

    notification_sent = None

    if result.coach_telegram_id is not None:
        notification_sent = await send_logged_message(
            bot=callback.bot,
            chat_id=result.coach_telegram_id,
            text=(
                "Клиент отменил запись.\n\n"
                f"Клиент: {result.client_display_name or 'без имени'}\n"
                f"Время: {slot_time}\n"
                f"Часовой пояс: {timezone_name}\n\n"
                "Слот снова доступен для бронирования."
            ),
            notification_type="appointment_cancelled_by_client",
            related_entity_type="appointment",
            related_entity_id=appointment_id,
        )

    if notification_sent is not None and notification_sent.ok:
        await callback.message.edit_text("Запись отменена. Тренер получил уведомление.")
    else:
        await callback.message.edit_text(
            "Запись отменена, но уведомление тренеру отправить не удалось."
        )
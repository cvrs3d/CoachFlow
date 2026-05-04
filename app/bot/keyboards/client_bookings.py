from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import Appointment, AvailabilitySlot
from app.utils.datetime import format_slot_range_for_timezone


def client_bookings_keyboard(
    items: list[tuple[Appointment, AvailabilitySlot]],
    timezone_name: str = "Europe/Prague",
) -> InlineKeyboardMarkup:
    keyboard = []

    for appointment, slot in items:
        slot_time = format_slot_range_for_timezone(
            slot.starts_at,
            slot.ends_at,
            timezone_name,
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=slot_time,
                    callback_data=f"client_booking:open:{appointment.id}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def client_booking_card_keyboard(
    appointment_id: str,
    can_cancel: bool,
) -> InlineKeyboardMarkup:
    keyboard = []

    if can_cancel:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="❌ Отменить запись",
                    callback_data=f"client_booking:confirm_cancel:{appointment_id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к моим записям",
                callback_data="client_booking:list",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def confirm_cancel_client_booking_keyboard(appointment_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, отменить",
                    callback_data=f"client_booking:cancel:{appointment_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"client_booking:open:{appointment_id}",
                )
            ],
        ]
    )   
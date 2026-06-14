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
                    callback_data=f"c_b:o:{appointment.id}",
                )
            ]
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text="📎 Скачать календарь",
                    callback_data="c_b:ics_all",
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
                    callback_data=f"c_b:c_c:{appointment_id}",
                )
            ]
        )
    
    keyboard.append(
        [
            InlineKeyboardButton(
                text="📎 Добавить в календарь",
                callback_data=f"c_b:ics:{appointment_id}",
            )
        ]
    )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад к моим записям",
                callback_data="c_b:l",
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
                    callback_data=f"c_b:c:{appointment_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"c_b:o:{appointment_id}",
                )
            ],
        ]
    )

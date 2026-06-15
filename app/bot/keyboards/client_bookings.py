from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t
from app.db.models import Appointment, AvailabilitySlot
from app.utils.datetime import format_slot_range_for_timezone


def client_bookings_keyboard(
    items: list[tuple[Appointment, AvailabilitySlot]],
    timezone_name: str = "Europe/Prague",
    language_code: str = "ru",
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
                text=t("client_bookings.download_calendar", language_code),
                callback_data="c_b:ics_all",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def client_booking_card_keyboard(
    appointment_id: str,
    can_cancel: bool,
    language_code: str = "ru",
) -> InlineKeyboardMarkup:
    keyboard = []

    if can_cancel:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=t("client_bookings.cancel_booking", language_code),
                    callback_data=f"c_b:c_c:{appointment_id}",
                )
            ]
        )
    
    keyboard.append(
        [
            InlineKeyboardButton(
                text=t("client_bookings.add_to_calendar", language_code),
                callback_data=f"c_b:ics:{appointment_id}",
            )
        ]
    )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=t("client_bookings.back_to_my_bookings", language_code),
                callback_data="c_b:l",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def confirm_cancel_client_booking_keyboard(appointment_id: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("client_bookings.confirm_cancel", language_code),
                    callback_data=f"c_b:c:{appointment_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("client_bookings.back", language_code),
                    callback_data=f"c_b:o:{appointment_id}",
                )
            ],
        ]
    )

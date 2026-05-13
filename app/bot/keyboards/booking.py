from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import AvailabilitySlot
from app.utils.datetime import format_slot_range_for_timezone


def available_slots_keyboard(
    slots: list[AvailabilitySlot],
    timezone_name: str = "Europe/Prague",
) -> InlineKeyboardMarkup:
    keyboard = []

    for slot in slots:
        label = format_slot_range_for_timezone(
            slot.starts_at,
            slot.ends_at,
            timezone_name,
        )

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"book_slot:{slot.id}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

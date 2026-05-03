from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import AvailabilitySlot


def available_slots_keyboard(slots: list[AvailabilitySlot]) -> InlineKeyboardMarkup:
    keyboard = []

    for slot in slots:
        starts_at = slot.starts_at

        if isinstance(starts_at, str):
            label = starts_at
        else:
            label = starts_at.strftime("%Y-%m-%d %H:%M")

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"book_slot:{slot.id}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def coach_schedule_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить слот",
                    callback_data="schedule:add_slot",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Мои слоты",
                    callback_data="schedule:list_slots",
                )
            ],
        ]
    )


def slot_duration_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="30 мин", callback_data="slot_duration:30"),
                InlineKeyboardButton(text="45 мин", callback_data="slot_duration:45"),
            ],
            [
                InlineKeyboardButton(text="60 мин", callback_data="slot_duration:60"),
                InlineKeyboardButton(text="90 мин", callback_data="slot_duration:90"),
            ],
        ]
    )
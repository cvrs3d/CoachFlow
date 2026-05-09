from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def meal_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Завтрак",
                    callback_data="mr:t:breakfast",
                ),
                InlineKeyboardButton(
                    text="Обед",
                    callback_data="mr:t:lunch",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Ужин",
                    callback_data="mr:t:dinner",
                ),
                InlineKeyboardButton(
                    text="Перекус",
                    callback_data="mr:t:snack",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Другое",
                    callback_data="mr:t:other",
                ),
            ],
        ]
    )
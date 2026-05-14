from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def meal_checkin_schedule_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Создать дефолтное расписание",
                    callback_data="mcs:create_default",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Сгенерировать check-ins на сегодня",
                    callback_data="mcs:generate_today",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📅 Сгенерировать check-ins на завтра",
                    callback_data="mcs:generate_tomorrow",
                )
            ],
        ]
    )
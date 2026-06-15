from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t


def meal_checkin_schedule_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("meal_checkins.create_default", language_code),
                    callback_data="mcs:create_default",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("meal_checkins.generate_today", language_code),
                    callback_data="mcs:generate_today",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("meal_checkins.generate_tomorrow", language_code),
                    callback_data="mcs:generate_tomorrow",
                )
            ],
        ]
    )
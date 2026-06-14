from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from app.bot.i18n import t


def coach_main_menu(language_code: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("menu.overview", language_code))],
            [KeyboardButton(text=t("menu.create_invite", language_code))],
            [
                KeyboardButton(text=t("menu.schedule", language_code)),
                KeyboardButton(text=t("menu.clients", language_code)),
            ],
            [
                KeyboardButton(text=t("menu.meal_reports", language_code)),
                KeyboardButton(text=t("menu.meal_schedule", language_code)),
            ],
            [KeyboardButton(text=t("menu.language", language_code))],
        ],
        resize_keyboard=True,
        input_field_placeholder=t("menu.placeholder", language_code),
    )


def client_main_menu(language_code: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=t("menu.choose_time", language_code)),
                KeyboardButton(text=t("menu.my_bookings", language_code)),
            ],
            [
                KeyboardButton(text=t("menu.send_meal_photo", language_code)),
                KeyboardButton(text=t("menu.my_meal_reports", language_code)),
            ],
            [
                KeyboardButton(text=t("menu.profile", language_code)),
                KeyboardButton(text=t("menu.language", language_code)),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder=t("menu.placeholder", language_code),
    )
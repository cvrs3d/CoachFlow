from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks.menu import MainMenuCallback
from app.bot.i18n import t


def coach_main_menu(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("menu.overview", language_code),
                    callback_data=MainMenuCallback(action="coach_dashboard").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("menu.create_invite", language_code),
                    callback_data=MainMenuCallback(action="coach_invite").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("menu.schedule", language_code),
                    callback_data=MainMenuCallback(action="coach_schedule").pack(),
                ),
                InlineKeyboardButton(
                    text=t("menu.clients", language_code),
                    callback_data=MainMenuCallback(action="coach_clients").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("menu.meal_reports", language_code),
                    callback_data=MainMenuCallback(action="coach_meal_reports").pack(),
                ),
                InlineKeyboardButton(
                    text=t("menu.meal_schedule", language_code),
                    callback_data=MainMenuCallback(action="coach_meal_schedule").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("menu.language", language_code),
                    callback_data=MainMenuCallback(action="language").pack(),
                )
            ],
        ]
    )


def client_main_menu(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("menu.choose_time", language_code),
                    callback_data=MainMenuCallback(action="client_booking").pack(),
                ),
                InlineKeyboardButton(
                    text=t("menu.my_bookings", language_code),
                    callback_data=MainMenuCallback(action="client_bookings").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("menu.send_meal_photo", language_code),
                    callback_data=MainMenuCallback(action="client_meal_submit").pack(),
                ),
                InlineKeyboardButton(
                    text=t("menu.my_meal_reports", language_code),
                    callback_data=MainMenuCallback(action="client_meal_reports").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("menu.profile", language_code),
                    callback_data=MainMenuCallback(action="client_profile").pack(),
                ),
                InlineKeyboardButton(
                    text=t("menu.language", language_code),
                    callback_data=MainMenuCallback(action="language").pack(),
                ),
            ],
        ]
    )
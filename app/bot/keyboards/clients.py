from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t
from app.db.models import Client


def client_appointments_keyboard(client_id: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("clients.back_to_card", language_code),
                    callback_data=f"client:open:{client_id}",
                )
            ]
        ]
    )


def clients_list_keyboard(clients: list[Client], language_code: str = "ru") -> InlineKeyboardMarkup:
    keyboard = []

    for client in clients:
        name = client.display_name or t("clients.without_name", language_code)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=name,
                    callback_data=f"client:open:{client.id}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def client_card_keyboard(client_id: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("clients.bookings", language_code),
                    callback_data=f"cc:bookings:{client_id}",
                ),
                InlineKeyboardButton(
                    text=t("clients.meal_reports", language_code),
                    callback_data=f"cc:meals:{client_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("clients.edit_name", language_code),
                    callback_data=f"client:edit_name:{client_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("clients.deactivate", language_code),
                    callback_data=f"client:delete:{client_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("clients.back_to_clients", language_code),
                    callback_data="clients:list",
                ),
            ],
        ]
    )


def confirm_delete_client_keyboard(client_id: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("clients.confirm_delete", language_code),
                    callback_data=f"client:delete:{client_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("clients.back", language_code),
                    callback_data=f"client:open:{client_id}",
                )
            ],
        ]
    )

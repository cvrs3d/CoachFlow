from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import Client


def clients_list_keyboard(clients: list[Client]) -> InlineKeyboardMarkup:
    keyboard = []

    for client in clients:
        name = client.display_name or "Без имени"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=name,
                    callback_data=f"client:open:{client.id}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def client_card_keyboard(client_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📅 Записи",
                    callback_data=f"cc:bookings:{client_id}",
                ),
                InlineKeyboardButton(
                    text="🍽 Отчеты еды",
                    callback_data=f"cc:meals:{client_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить имя",
                    callback_data=f"client:edit_name:{client_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🚫 Деактивировать",
                    callback_data=f"client:delete:{client_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К клиентам",
                    callback_data="clients:list",
                ),
            ],
        ]
    )

def confirm_delete_client_keyboard(client_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить",
                    callback_data=f"client:delete:{client_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"client:open:{client_id}",
                )
            ],
        ]
    )
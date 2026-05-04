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
                    text="✏️ Изменить имя",
                    callback_data=f"client:edit_name:{client_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить клиента",
                    callback_data=f"client:delete:{client_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к клиентам",
                    callback_data="client:list",
                )
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
from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.clients import client_card_keyboard, clients_list_keyboard
from app.services.clients import get_client_card_for_coach, list_clients_for_coach

router = Router()


@router.message(F.text == "👥 Клиенты")
async def clients_menu_handler(message: Message) -> None:
    clients = await list_clients_for_coach(message.from_user.id)

    if not clients:
        await message.answer("У вас пока нет активных клиентов.")
        return

    await message.answer(
        "Ваши клиенты:",
        reply_markup=clients_list_keyboard(clients),
    )


@router.callback_query(F.data == "client:list")
async def clients_list_callback_handler(callback: CallbackQuery) -> None:
    clients = await list_clients_for_coach(callback.from_user.id)

    await callback.answer()

    if not clients:
        await callback.message.edit_text("У вас пока нет активных клиентов.")
        return

    await callback.message.edit_text(
        "Ваши клиенты:",
        reply_markup=clients_list_keyboard(clients),
    )


@router.callback_query(F.data.startswith("client:open:"))
async def open_client_card_handler(callback: CallbackQuery) -> None:
    client_id = callback.data.split(":", 2)[2]

    card = await get_client_card_for_coach(
        telegram_id=callback.from_user.id,
        client_id=client_id,
    )

    await callback.answer()

    if card is None:
        await callback.message.edit_text(
            "Клиент не найден или у вас нет доступа."
        )
        return

    client = card.client
    user = card.user

    text = (
        "Карточка клиента\n\n"
        f"Имя: {client.display_name or 'не указано'}\n"
        f"Статус клиента: {client.status}\n"
        f"Telegram username: @{user.username}\n" if user.username else
        "Карточка клиента\n\n"
        f"Имя: {client.display_name or 'не указано'}\n"
        f"Статус клиента: {client.status}\n"
        "Telegram username: не указан\n"
    )

    text += (
        f"Telegram ID: {user.telegram_id}\n"
        f"Активных записей: {card.future_appointments_count}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=client_card_keyboard(client.id),
    )
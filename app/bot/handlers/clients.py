from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext


from app.bot.keyboards.clients import client_card_keyboard, clients_list_keyboard
from app.bot.states.clients import ClientEditStates
from app.services.clients import (
    get_client_card_for_coach,
    get_client_display_name_for_coach,
    list_clients_for_coach,
    update_client_display_name_for_coach,
)

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

    username_text = f"@{user.username}" if user.username else "не указан"

    text = (
        "Карточка клиента\n\n"
        f"Имя: {client.display_name or 'не указано'}\n"
        f"Статус клиента: {client.status}\n"
        f"Telegram username: {username_text}\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Активных записей: {card.future_appointments_count}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=client_card_keyboard(client.id),
    )

@router.callback_query(F.data.startswith("client:edit_name:"))
async def edit_client_name_start_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    client_id = callback.data.split(":", 2)[2]

    current_name = await get_client_display_name_for_coach(
        telegram_id=callback.from_user.id,
        client_id=client_id,
    )

    await callback.answer()

    if current_name is None:
        await callback.message.edit_text(
            "Клиент не найден или у вас нет доступа."
        )
        return

    await state.set_state(ClientEditStates.waiting_for_new_display_name)
    await state.update_data(client_id=client_id)

    await callback.message.answer(
        "Введите новое имя клиента.\n\n"
        f"Текущее имя: {current_name or 'не указано'}"
    )

@router.message(ClientEditStates.waiting_for_new_display_name)
async def edit_client_name_process_handler(
    message: Message,
    state: FSMContext,
) -> None:
    new_name = (message.text or "").strip()

    if len(new_name) < 2:
        await message.answer("Имя слишком короткое. Введите минимум 2 символа.")
        return

    if len(new_name) > 80:
        await message.answer("Имя слишком длинное. Введите до 80 символов.")
        return

    data = await state.get_data()
    client_id = data.get("client_id")

    if not client_id:
        await state.clear()
        await message.answer("Не удалось определить клиента. Откройте карточку заново.")
        return

    ok = await update_client_display_name_for_coach(
        telegram_id=message.from_user.id,
        client_id=client_id,
        new_display_name=new_name,
    )

    await state.clear()

    if not ok:
        await message.answer("Не удалось обновить имя клиента.")
        return

    card = await get_client_card_for_coach(
        telegram_id=message.from_user.id,
        client_id=client_id,
    )

    if card is None:
        await message.answer("Имя обновлено.")
        return

    client = card.client
    user = card.user

    username_text = f"@{user.username}" if user.username else "не указан"

    text = (
        "Карточка клиента\n\n"
        f"Имя: {client.display_name or 'не указано'}\n"
        f"Статус клиента: {client.status}\n"
        f"Telegram username: {username_text}\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Активных записей: {card.future_appointments_count}"
    )

    await message.answer(
        text,
        reply_markup=client_card_keyboard(client.id),
    )
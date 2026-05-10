from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext


from app.bot.keyboards.clients import (
    clients_list_keyboard,
    confirm_delete_client_keyboard,
)
from app.bot.states.clients import ClientEditStates
from app.services.clients import (
    deactivate_client_for_coach,
    get_client_display_name_for_coach,
    list_clients_for_coach,
    update_client_display_name_for_coach,
)

from app.bot.keyboards.clients import client_card_keyboard
from app.services.client_cards import get_client_card_for_coach
from app.utils.datetime import format_slot_range_for_timezone

router = Router()


def format_client_card_text(result) -> str:
    assert result.card is not None

    card = result.card
    client = card.client
    user = card.user
    stats = card.stats

    client_name = client.display_name or "без имени"
    username = f"@{user.username}" if user.username else "не указан"

    if card.upcoming_appointment is None:
        upcoming_text = "нет будущих записей"
    else:
        upcoming_text = format_slot_range_for_timezone(
            card.upcoming_appointment.starts_at,
            card.upcoming_appointment.ends_at,
            result.coach_timezone or "Europe/Prague",
        )

    return (
        f"👤 Клиент: {client_name}\n\n"
        f"Telegram username: {username}\n"
        f"Статус: {client.status}\n\n"
        f"Ближайшая запись:\n"
        f"{upcoming_text}\n\n"
        f"Food reports за 7 дней:\n"
        f"- отправлено: {stats.reports_7d_count}\n"
        f"- проверено: {stats.reviewed_7d_count}\n"
        f"- требует улучшения: {stats.needs_improvement_7d_count}\n"
        f"- ждет ответа клиента: {stats.waiting_clarification_count}"
    )

@router.callback_query(F.data.startswith("cc:bookings:"))
async def client_card_bookings_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("Раздел записей клиента добавим следующим шагом.")


@router.callback_query(F.data.startswith("cc:meals:"))
async def client_card_meals_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    await callback.message.answer("Раздел отчетов еды клиента добавим следующим шагом.")

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

    result = await get_client_card_for_coach(
        coach_telegram_id=callback.from_user.id,
        client_id=client_id,
    )

    await callback.answer()

    if not result.ok or result.card is None:
        await callback.message.answer("Клиент не найден или у вас нет доступа.")
        return

    await callback.message.answer(
        format_client_card_text(result),
        reply_markup=client_card_keyboard(client_id),
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

    result = await get_client_card_for_coach(
        telegram_id=message.from_user.id,
        client_id=client_id,
    )

    if result is None:
        await message.answer("Имя обновлено.")
        return

    client = result.card.client
    
    await message.answer(
        format_client_card_text(result),
        reply_markup=client_card_keyboard(client.id),
    )

@router.callback_query(F.data.startswith("client:confirm_delete:"))
async def confirm_delete_client_handler(callback: CallbackQuery) -> None:
    client_id = callback.data.split(":", 2)[2]

    result = await get_client_card_for_coach(
        telegram_id=callback.from_user.id,
        client_id=client_id,
    )

    await callback.answer()

    if result is None:
        await callback.message.edit_text(
            "Клиент не найден или у вас нет доступа."
        )
        return
    
    card = result.card

    await callback.message.edit_text(
        "Удалить клиента?\n\n"
        f"Клиент: {card.client.display_name or 'без имени'}\n\n"
        "Клиент будет деактивирован. Его будущие записи будут отменены, "
        "а занятые слоты снова станут доступными.",
        reply_markup=confirm_delete_client_keyboard(client_id),
    )


@router.callback_query(F.data.startswith("client:delete:"))
async def delete_client_handler(callback: CallbackQuery) -> None:
    client_id = callback.data.split(":", 2)[2]

    ok = await deactivate_client_for_coach(
        telegram_id=callback.from_user.id,
        client_id=client_id,
    )

    await callback.answer()

    if not ok:
        await callback.message.edit_text(
            "Не удалось удалить клиента. Клиент не найден или у вас нет доступа."
        )
        return

    clients = await list_clients_for_coach(callback.from_user.id)

    if not clients:
        await callback.message.edit_text(
            "Клиент удален.\n\n"
            "У вас больше нет активных клиентов."
        )
        return

    await callback.message.edit_text(
        "Клиент удален.\n\n"
        "Ваши клиенты:",
        reply_markup=clients_list_keyboard(clients),
    )
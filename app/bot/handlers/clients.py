from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.menu import MainMenuCallback
from app.bot.formatters.clients import (
    format_client_appointments_text,
    format_client_card_text,
)
from app.bot.keyboards.clients import (
    client_appointments_keyboard,
    client_card_keyboard,
    clients_list_keyboard,
    confirm_delete_client_keyboard,
)
from app.bot.i18n import get_user_language, t
from app.bot.keyboards.common import cancel_keyboard
from app.bot.keyboards.meal_reports import coach_client_meal_reports_keyboard
from app.bot.states.clients import ClientEditStates
from app.bot.utils.safe_messages import safe_answer_or_edit_text
from app.services.client_appointments import list_client_appointments_for_coach
from app.services.client_cards import get_client_card_for_coach
from app.services.clients import (
    deactivate_client_for_coach,
    get_client_display_name_for_coach,
    list_clients_for_coach,
    update_client_display_name_for_coach,
)
from app.services.meal_reports import list_meal_reports_for_coach_client

router = Router()


APPOINTMENT_STATUS_LABELS = {
    "booked": "запланирована",
    "cancelled_by_client": "отменена клиентом",
    "cancelled_by_coach": "отменена тренером",
    "completed": "завершена",
    "no_show": "не пришел",
}


@router.callback_query(F.data.startswith("cc:bookings:"))
async def client_card_bookings_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    client_id = callback.data.split(":", 2)[2]

    result = await list_client_appointments_for_coach(
        coach_telegram_id=callback.from_user.id,
        client_id=client_id,
        future_limit=5,
        history_limit=5,
    )

    await callback.answer()

    if not result.ok:
        if result.reason == "coach_not_found":
            await callback.message.answer(t("clients.access_denied", language_code))
            return

        if result.reason == "client_not_found":
            await safe_answer_or_edit_text(callback.message, t("clients.client_not_found", language_code))
            return

        await callback.message.answer(t("clients.open_bookings_failed", language_code))
        return

    await callback.message.answer(
        format_client_appointments_text(result, language_code),
        reply_markup=client_appointments_keyboard(client_id, language_code),
    )


@router.callback_query(F.data.startswith("cc:meals:"))
async def client_card_meal_reports_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    client_id = callback.data.split(":", 2)[2]

    reports = await list_meal_reports_for_coach_client(
        coach_telegram_id=callback.from_user.id,
        client_id=client_id,
        limit=10,
    )

    await callback.answer()

    if not reports:
        await callback.message.answer(t("clients.no_meal_reports", language_code))
        return

    client_name = reports[0][1].display_name or t("clients.without_name", language_code)

    await callback.message.answer(
        t("clients.meal_reports_title", language_code, client_name=client_name),
        reply_markup=coach_client_meal_reports_keyboard(
            reports,
            client_id=client_id,
            language_code=language_code,
        ),
    )


@router.callback_query(MainMenuCallback.filter(F.action == "coach_clients"))
async def clients_menu_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    await callback.answer()
    clients = await list_clients_for_coach(callback.from_user.id)
    if not clients:
        await callback.message.answer(t("clients.no_clients", language_code))
        return

    await callback.message.answer(
        t("clients.title", language_code),
        reply_markup=clients_list_keyboard(clients, language_code),
    )


@router.callback_query(F.data == "client:list")
async def clients_list_callback_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    clients = await list_clients_for_coach(callback.from_user.id)

    await callback.answer()

    if not clients:
        await safe_answer_or_edit_text(callback.message, t("clients.no_clients", language_code))
        return

    await safe_answer_or_edit_text(
        callback.message,
        t("clients.title", language_code),
        reply_markup=clients_list_keyboard(clients, language_code),
    )


@router.callback_query(F.data.startswith("client:open:"))
async def open_client_card_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    client_id = callback.data.split(":", 2)[2]

    result = await get_client_card_for_coach(
        coach_telegram_id=callback.from_user.id,
        client_id=client_id,
    )

    await callback.answer()

    if not result.ok or result.card is None:
        await safe_answer_or_edit_text(callback.message, t("clients.client_not_found", language_code))
        return

    await callback.message.answer(
        format_client_card_text(result, language_code),
        reply_markup=client_card_keyboard(client_id, language_code),
    )


@router.callback_query(F.data.startswith("client:edit_name:"))
async def edit_client_name_start_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    client_id = callback.data.split(":", 2)[2]
    language_code = await get_user_language(callback.from_user.id)

    current_name = await get_client_display_name_for_coach(
        telegram_id=callback.from_user.id,
        client_id=client_id,
    )

    await callback.answer()

    if current_name is None:
        await safe_answer_or_edit_text(callback.message, t("clients.client_not_found", language_code))
        return

    await state.set_state(ClientEditStates.waiting_for_new_display_name)
    await state.update_data(client_id=client_id)

    await callback.message.answer(
        f"{t('clients.edit_name_prompt', language_code, current_name=current_name or t('clients.without_name', language_code))}\n\n"
        f"{t('common.cancel', language_code)} /cancel",
        reply_markup=cancel_keyboard(language_code),
    )


@router.message(ClientEditStates.waiting_for_new_display_name)
async def edit_client_name_process_handler(
    message: Message,
    state: FSMContext,
) -> None:
    language_code = await get_user_language(message.from_user.id)
    new_name = (message.text or "").strip()

    if len(new_name) < 2:
        await message.answer(
            t("registration.name_too_short", language_code),
            reply_markup=cancel_keyboard(language_code),
        )
        return

    if len(new_name) > 80:
        await message.answer(
            t("registration.name_too_long", language_code),
            reply_markup=cancel_keyboard(language_code),
        )
        return

    data = await state.get_data()
    client_id = data.get("client_id")

    if not client_id:
        await state.clear()
        await message.answer(t("clients.client_unknown", language_code))
        return

    ok = await update_client_display_name_for_coach(
        telegram_id=message.from_user.id,
        client_id=client_id,
        new_display_name=new_name,
    )

    await state.clear()

    if not ok:
        await message.answer(t("clients.update_name_failed", language_code))
        return

    result = await get_client_card_for_coach(
        coach_telegram_id=message.from_user.id,
        client_id=client_id,
    )

    if not result.ok or result.card is None:
        await message.answer(t("clients.name_updated", language_code))
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
        coach_telegram_id=callback.from_user.id,
        client_id=client_id,
    )

    await callback.answer()

    if not result.ok or result.card is None:
        await safe_answer_or_edit_text(callback.message, t("clients.client_not_found", language_code))
        return

    card = result.card

    await safe_answer_or_edit_text(
        callback.message,
        t(
            "clients.confirm_delete",
            language_code,
            client_name=card.client.display_name or t("clients.without_name", language_code),
        ),
        reply_markup=confirm_delete_client_keyboard(client_id, language_code),
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
        await safe_answer_or_edit_text(callback.message, t("clients.delete_failed", language_code))
        return

    clients = await list_clients_for_coach(callback.from_user.id)

    if not clients:
        await safe_answer_or_edit_text(callback.message, t("clients.deleted_no_clients", language_code))
        return

    await safe_answer_or_edit_text(
        callback.message,
        t("clients.deleted", language_code),
        reply_markup=clients_list_keyboard(clients, language_code),
    )

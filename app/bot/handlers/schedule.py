from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message
from app.bot.callbacks.menu import MainMenuCallback
from app.bot.i18n import get_user_language, t
from app.bot.keyboards.common import cancel_keyboard

from app.bot.keyboards.schedule import (
    available_slot_management_keyboard,
    booked_slot_management_keyboard,
    coach_schedule_keyboard,
    coach_slots_keyboard,
    confirm_cancel_booked_slot_keyboard,
    slot_date_keyboard,
    slot_duration_keyboard,
    slot_time_keyboard,
)
from app.bot.states.schedule import ScheduleStates
from app.services.notifications import send_logged_message
from app.services.schedule import (
    create_availability_slot,
    get_coach_by_telegram_id,
    parse_coach_datetime,
)
from app.services.calendar_files import (
    build_coach_future_bookings_ics,
    build_coach_slot_appointment_ics,
)
from app.services.schedule_management import (
    cancel_booked_slot_for_coach,
    delete_available_slot_for_coach,
    get_slot_card_for_coach,
    list_coach_manageable_slots,
)
from app.utils.datetime import format_slot_range_for_timezone

router = Router()


def _with_cancel_keyboard(
    keyboard: InlineKeyboardMarkup,
    language_code: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=keyboard.inline_keyboard + cancel_keyboard(language_code).inline_keyboard,
    )


@router.callback_query(MainMenuCallback.filter(F.action == "coach_schedule"))
async def schedule_menu_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    coach = await get_coach_by_telegram_id(callback.from_user.id)

    await callback.answer()

    if coach is None:
        return

    await callback.message.answer(
        t("schedule.title", language_code),
        reply_markup=coach_schedule_keyboard(language_code),
    )


@router.callback_query(F.data == "schedule:add_slot")
async def add_slot_start_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    coach = await get_coach_by_telegram_id(callback.from_user.id)
    language_code = await get_user_language(callback.from_user.id)

    if coach is None:
        await callback.answer()
        return

    await state.set_state(ScheduleStates.waiting_for_slot_date)

    await callback.message.answer(
        f"{t('schedule.choose_date', language_code, timezone_name=coach.timezone)}\n\n"
        f"{t('common.cancel', language_code)} /cancel",
        reply_markup=_with_cancel_keyboard(
            slot_date_keyboard(coach.timezone, language_code=language_code),
            language_code,
        ),
    )

    await callback.answer()


@router.callback_query(
    ScheduleStates.waiting_for_slot_date,
    F.data.startswith("sd:"),
)
async def process_slot_date_button_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    date_value = callback.data.split(":", 1)[1]
    language_code = await get_user_language(callback.from_user.id)

    await callback.answer()

    if date_value == "manual":
        await callback.message.answer(
            f"{t('schedule.enter_date', language_code)}\n\n"
            f"{t('common.cancel', language_code)} /cancel",
            reply_markup=cancel_keyboard(language_code),
        )
        return

    await state.update_data(slot_date=date_value)
    await state.set_state(ScheduleStates.waiting_for_slot_start_time)

    await callback.message.edit_text(
        f"{t('schedule.date_selected', language_code, date_value=date_value)}\n\n"
        f"{t('common.cancel', language_code)} /cancel",
        reply_markup=_with_cancel_keyboard(
            slot_time_keyboard(start_hour=10, end_hour=18, language_code=language_code),
            language_code,
        ),
    )


@router.message(ScheduleStates.waiting_for_slot_date)
async def process_slot_date_handler(
    message: Message,
    state: FSMContext,
) -> None:
    language_code = await get_user_language(message.from_user.id)
    date_text = (message.text or "").strip()

    try:
        datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        await message.answer(
            f"{t('schedule.invalid_date', language_code)}\n\n{t('common.cancel', language_code)} /cancel",
            reply_markup=cancel_keyboard(language_code),
        )
        return

    await state.update_data(slot_date=date_text)
    await state.set_state(ScheduleStates.waiting_for_slot_start_time)

    await message.answer(
        f"{t('schedule.date_saved', language_code)}\n\n{t('common.cancel', language_code)} /cancel",
        reply_markup=_with_cancel_keyboard(
            slot_time_keyboard(start_hour=10, end_hour=18, language_code=language_code),
            language_code,
        ),
    )


@router.callback_query(
    ScheduleStates.waiting_for_slot_start_time,
    F.data.startswith("st:"),
)
async def process_slot_time_button_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    time_value = callback.data.split(":", 1)[1]
    language_code = await get_user_language(callback.from_user.id)

    await callback.answer()

    if time_value == "manual":
        await callback.message.answer(
            f"{t('schedule.enter_time', language_code)}\n\n{t('common.cancel', language_code)} /cancel",
            reply_markup=cancel_keyboard(language_code),
        )
        return

    await state.update_data(slot_start_time=time_value)
    await state.set_state(ScheduleStates.waiting_for_slot_duration)

    await callback.message.edit_text(
        f"{t('schedule.time_selected', language_code, time_value=time_value)}\n\n{t('common.cancel', language_code)} /cancel",
        reply_markup=_with_cancel_keyboard(slot_duration_keyboard(language_code), language_code),
    )


@router.message(ScheduleStates.waiting_for_slot_start_time)
async def process_slot_start_time_handler(
    message: Message,
    state: FSMContext,
) -> None:
    language_code = await get_user_language(message.from_user.id)
    time_text = (message.text or "").strip()

    try:
        datetime.strptime(time_text, "%H:%M")
    except ValueError:
        await message.answer(
            f"{t('schedule.invalid_time', language_code)}\n\n{t('common.cancel', language_code)} /cancel",
            reply_markup=cancel_keyboard(language_code),
        )
        return

    await state.update_data(slot_start_time=time_text)
    await state.set_state(ScheduleStates.waiting_for_slot_duration)

    await message.answer(
        f"{t('schedule.time_saved', language_code)}\n\n{t('common.cancel', language_code)} /cancel",
        reply_markup=_with_cancel_keyboard(slot_duration_keyboard(language_code), language_code),
    )


@router.callback_query(
    ScheduleStates.waiting_for_slot_duration,
    F.data.startswith("slot_duration:"),
)
async def process_slot_duration_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    coach = await get_coach_by_telegram_id(callback.from_user.id)

    if coach is None:
        await callback.answer()
        await state.clear()
        return

    duration_minutes = int(callback.data.split(":")[1])

    data = await state.get_data()
    date_text = data["slot_date"]
    time_text = data["slot_start_time"]

    starts_at = parse_coach_datetime(
        date_text=date_text,
        time_text=time_text,
        timezone_name=coach.timezone,
    )

    result = await create_availability_slot(
        coach_id=coach.id,
        starts_at=starts_at,
        duration_minutes=duration_minutes,
    )

    await state.clear()
    await callback.answer()

    if not result.ok:
        if result.reason == "overlap":
            await callback.message.answer(t("schedule.slot_overlap", language_code))
            return

        await callback.message.answer(t("schedule.slot_create_failed", language_code))
        return

    await callback.message.answer(
        t(
            "schedule.slot_created",
            language_code,
            date_text=date_text,
            time_text=time_text,
            duration_minutes=duration_minutes,
            timezone_name=coach.timezone,
        )
    )


@router.callback_query(F.data == "schedule:list_slots")
async def list_slots_handler(callback: CallbackQuery) -> None:
    coach = await get_coach_by_telegram_id(callback.from_user.id)

    if coach is None:
        await callback.answer()
        return

    slots = await list_coach_manageable_slots(
        telegram_id=callback.from_user.id,
        limit=20,
    )

    await callback.answer()

    if not slots:
        await callback.message.edit_text(t("schedule.no_slots", language_code))
        return

    await callback.message.edit_text(
        t("schedule.future_slots_title", language_code, timezone_name=coach.timezone),
        reply_markup=coach_slots_keyboard(slots, coach.timezone, language_code),
    )


@router.callback_query(F.data.startswith("schedule:open_slot:"))
async def open_slot_handler(callback: CallbackQuery) -> None:
    slot_id = callback.data.split(":", 2)[2]

    card = await get_slot_card_for_coach(
        telegram_id=callback.from_user.id,
        slot_id=slot_id,
    )

    coach = await get_coach_by_telegram_id(callback.from_user.id)
    timezone_name = coach.timezone if coach else "Europe/Prague"

    await callback.answer()

    if card is None:
        await callback.message.edit_text(t("schedule.slot_not_found", language_code))
        return

    slot = card.slot

    slot_time = format_slot_range_for_timezone(
        slot.starts_at,
        slot.ends_at,
        timezone_name,
    )
    if slot.status == "available":
        text = (
            f"{t('schedule.free_slot_card', language_code, slot_time=slot_time, timezone_name=timezone_name)}"
        )

        await callback.message.edit_text(
            text,
            reply_markup=available_slot_management_keyboard(slot.id),
        )
        return

    if slot.status == "booked":
        client_name = "неизвестный клиент"

        if card.client is not None:
            client_name = card.client.display_name or t("clients.without_name", language_code)

        text = (
            f"{t('schedule.busy_slot_card', language_code, slot_time=slot_time, timezone_name=timezone_name, client_name=client_name)}"
        )

        await callback.message.edit_text(
            text,
            reply_markup=booked_slot_management_keyboard(slot.id),
        )
        return

    await callback.message.edit_text(t("schedule.slot_cancelled", language_code))


@router.callback_query(F.data.startswith("schedule:delete_available:"))
async def delete_available_slot_handler(callback: CallbackQuery) -> None:
    slot_id = callback.data.split(":", 2)[2]

    ok = await delete_available_slot_for_coach(
        telegram_id=callback.from_user.id,
        slot_id=slot_id,
    )

    await callback.answer()

    if not ok:
        await callback.message.edit_text(
            t("schedule.delete_failed", language_code)
        )
        return

    slots = await list_coach_manageable_slots(
        telegram_id=callback.from_user.id,
        limit=20,
    )

    if not slots:
        await callback.message.edit_text(
            t("schedule.deleted_no_slots", language_code)
        )
        return

    coach = await get_coach_by_telegram_id(callback.from_user.id)
    timezone_name = coach.timezone if coach else "Europe/Prague"

    await callback.message.edit_text(
        t("schedule.deleted", language_code),
        reply_markup=coach_slots_keyboard(slots, timezone_name, language_code),
    )


@router.callback_query(F.data.startswith("sc:cb:"))
async def cancel_booked_slot_confirm_handler(callback: CallbackQuery) -> None:
    slot_id = callback.data.split(":", 2)[2]

    card = await get_slot_card_for_coach(
        telegram_id=callback.from_user.id,
        slot_id=slot_id,
    )

    await callback.answer()

    if card is None or card.slot.status != "booked":
        await callback.message.edit_text(t("schedule.cancel_booking_not_found", language_code))
        return

    client_name = "неизвестный клиент"

    if card.client is not None:
        client_name = card.client.display_name or t("clients.without_name", language_code)

    coach = await get_coach_by_telegram_id(callback.from_user.id)
    timezone_name = coach.timezone if coach else "Europe/Prague"

    slot_time = format_slot_range_for_timezone(
        card.slot.starts_at,
        card.slot.ends_at,
        timezone_name,
    )

    await callback.message.edit_text(
        t(
            "schedule.cancel_booking_confirm",
            language_code,
            client_name=client_name,
            slot_time=slot_time,
            timezone_name=timezone_name,
        ),
        reply_markup=confirm_cancel_booked_slot_keyboard(slot_id),
    )


@router.callback_query(F.data.startswith("sc:ccb:"))
async def cancel_booked_slot_handler(callback: CallbackQuery) -> None:
    slot_id = callback.data.split(":", 2)[2]

    result = await cancel_booked_slot_for_coach(
        telegram_id=callback.from_user.id,
        slot_id=slot_id,
    )

    coach = await get_coach_by_telegram_id(callback.from_user.id)
    timezone_name = coach.timezone if coach else "Europe/Prague"

    await callback.answer()

    if not result.ok:
        await callback.message.edit_text(t("schedule.cancel_booking_failed", language_code))
        return

    starts_at = result.starts_at
    ends_at = result.ends_at

    if isinstance(starts_at, str):
        starts_at = datetime.fromisoformat(starts_at)

    if isinstance(ends_at, str):
        ends_at = datetime.fromisoformat(ends_at)

    slot_time = format_slot_range_for_timezone(
        starts_at,
        ends_at,
        timezone_name,
    )

    notification_sent = None

    if result.client_telegram_id is not None:
        notification_sent = await send_logged_message(
            bot=callback.bot,
            chat_id=result.client_telegram_id,
            text=(
                f"{t('schedule.client_cancel_notification', language_code, slot_time=slot_time, timezone_name=timezone_name)}"
            ),
            notification_type="appointment_cancelled_by_coach",
            related_entity_type="availability_slot",
            related_entity_id=slot_id,
        )

    if notification_sent is not None and notification_sent.ok:
        await callback.message.edit_text(t("schedule.cancel_booking_sent", language_code))
    else:
        await callback.message.edit_text(
            t("schedule.cancel_booking_not_available", language_code)
        )

@router.callback_query(F.data == "schedule:ics")
async def download_coach_future_bookings_ics_handler(callback: CallbackQuery) -> None:
    result = await build_coach_future_bookings_ics(
        telegram_id=callback.from_user.id,
    )

    await callback.answer()

    if not result.ok or result.file_bytes is None or result.filename is None:
        await callback.message.answer(t("schedule.ics_none", language_code))
        return

    await callback.message.answer_document(
        BufferedInputFile(
            result.file_bytes,
            filename=result.filename,
        ),
        caption=t("schedule.ics_caption", language_code),
    )


@router.callback_query(F.data.startswith("sc:ics:"))
async def download_coach_slot_appointment_ics_handler(callback: CallbackQuery) -> None:
    slot_id = callback.data.split(":", 2)[2]

    result = await build_coach_slot_appointment_ics(
        telegram_id=callback.from_user.id,
        slot_id=slot_id,
    )

    await callback.answer()

    if not result.ok or result.file_bytes is None or result.filename is None:
        await callback.message.answer(t("schedule.slot_ics_failed", language_code))
        return

    await callback.message.answer_document(
        BufferedInputFile(
            result.file_bytes,
            filename=result.filename,
        ),
        caption=t("schedule.slot_ics_caption", language_code),
    )
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, BufferedInputFile

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


@router.message(F.text == "📅 Расписание")
async def schedule_menu_handler(message: Message) -> None:
    coach = await get_coach_by_telegram_id(message.from_user.id)

    if coach is None:
        return

    await message.answer(
        "Расписание тренера.",
        reply_markup=coach_schedule_keyboard(),
    )


@router.callback_query(F.data == "schedule:add_slot")
async def add_slot_start_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    coach = await get_coach_by_telegram_id(callback.from_user.id)

    if coach is None:
        await callback.answer()
        return

    await state.set_state(ScheduleStates.waiting_for_slot_date)

    await callback.message.answer(
        f"Выберите дату слота.\n\nЧасовой пояс: {coach.timezone}",
        reply_markup=slot_date_keyboard(coach.timezone),
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

    await callback.answer()

    if date_value == "manual":
        await callback.message.answer(
            "Введите дату слота в формате YYYY-MM-DD.\n\nНапример: 2026-05-10"
        )
        return

    await state.update_data(slot_date=date_value)
    await state.set_state(ScheduleStates.waiting_for_slot_start_time)

    await callback.message.edit_text(
        f"Дата выбрана: {date_value}\n\nТеперь выберите время начала:",
        reply_markup=slot_time_keyboard(start_hour=10, end_hour=18),
    )


@router.message(ScheduleStates.waiting_for_slot_date)
async def process_slot_date_handler(
    message: Message,
    state: FSMContext,
) -> None:
    date_text = (message.text or "").strip()

    try:
        datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        await message.answer(
            "Неверный формат даты.\n\nВведите дату в формате YYYY-MM-DD. Например: 2026-05-10"
        )
        return

    await state.update_data(slot_date=date_text)
    await state.set_state(ScheduleStates.waiting_for_slot_start_time)

    await message.answer(
        "Дата сохранена.\n\nТеперь выберите время начала:",
        reply_markup=slot_time_keyboard(start_hour=10, end_hour=18),
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

    await callback.answer()

    if time_value == "manual":
        await callback.message.answer("Введите время начала в формате HH:MM.\n\nНапример: 14:30")
        return

    await state.update_data(slot_start_time=time_value)
    await state.set_state(ScheduleStates.waiting_for_slot_duration)

    await callback.message.edit_text(
        f"Время выбрано: {time_value}\n\nВыберите длительность слота:",
        reply_markup=slot_duration_keyboard(),
    )


@router.message(ScheduleStates.waiting_for_slot_start_time)
async def process_slot_start_time_handler(
    message: Message,
    state: FSMContext,
) -> None:
    time_text = (message.text or "").strip()

    try:
        datetime.strptime(time_text, "%H:%M")
    except ValueError:
        await message.answer(
            "Неверный формат времени.\n\nВведите время в формате HH:MM. Например: 14:30"
        )
        return

    await state.update_data(slot_start_time=time_text)
    await state.set_state(ScheduleStates.waiting_for_slot_duration)

    await message.answer(
        "Время сохранено.\n\nВыберите длительность слота:",
        reply_markup=slot_duration_keyboard(),
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
            await callback.message.answer(
                "Нельзя создать слот: это время пересекается с уже существующим слотом."
            )
            return

        await callback.message.answer("Не удалось создать слот.")
        return

    await callback.message.answer(
        "Слот создан.\n\n"
        f"Дата и время: {date_text} {time_text}\n"
        f"Длительность: {duration_minutes} мин\n"
        f"Часовой пояс: {coach.timezone}"
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
        await callback.message.edit_text("У вас пока нет будущих активных слотов.")
        return

    await callback.message.edit_text(
        f"Ваши будущие слоты.\nВремя указано в часовом поясе: {coach.timezone}",
        reply_markup=coach_slots_keyboard(slots, coach.timezone),
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
        await callback.message.edit_text("Слот не найден или у вас нет доступа.")
        return

    slot = card.slot

    slot_time = format_slot_range_for_timezone(
        slot.starts_at,
        slot.ends_at,
        timezone_name,
    )
    if slot.status == "available":
        text = (
            f"Карточка слота\n\nВремя: {slot_time}\nЧасовой пояс: {timezone_name}\nСтатус: свободен"
        )

        await callback.message.edit_text(
            text,
            reply_markup=available_slot_management_keyboard(slot.id),
        )
        return

    if slot.status == "booked":
        client_name = "неизвестный клиент"

        if card.client is not None:
            client_name = card.client.display_name or "без имени"

        text = (
            "Карточка слота\n\n"
            f"Время: {slot_time}\n"
            f"Часовой пояс: {timezone_name}\n"
            "Статус: занят\n"
            f"Клиент: {client_name}"
        )

        await callback.message.edit_text(
            text,
            reply_markup=booked_slot_management_keyboard(slot.id),
        )
        return

    await callback.message.edit_text("Этот слот уже отменен.")


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
            "Не удалось удалить слот. Возможно, он уже занят или отменен."
        )
        return

    slots = await list_coach_manageable_slots(
        telegram_id=callback.from_user.id,
        limit=20,
    )

    if not slots:
        await callback.message.edit_text(
            "Слот удален.\n\nУ вас больше нет будущих активных слотов."
        )
        return

    coach = await get_coach_by_telegram_id(callback.from_user.id)
    timezone_name = coach.timezone if coach else "Europe/Prague"

    await callback.message.edit_text(
        "Слот удален.\n\nВаши будущие слоты:",
        reply_markup=coach_slots_keyboard(slots, timezone_name),
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
        await callback.message.edit_text("Слот не найден или уже не является занятым.")
        return

    client_name = "неизвестный клиент"

    if card.client is not None:
        client_name = card.client.display_name or "без имени"

    coach = await get_coach_by_telegram_id(callback.from_user.id)
    timezone_name = coach.timezone if coach else "Europe/Prague"

    slot_time = format_slot_range_for_timezone(
        card.slot.starts_at,
        card.slot.ends_at,
        timezone_name,
    )

    await callback.message.edit_text(
        "Отменить занятие?\n\n"
        f"Клиент: {client_name}\n"
        f"Время: {slot_time}\n"
        f"Часовой пояс: {timezone_name}\n\n"
        "Клиент получит уведомление об отмене.",
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
        await callback.message.edit_text("Не удалось отменить занятие. Возможно, оно уже отменено.")
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
                "Ваше занятие отменено тренером.\n\n"
                f"Время: {slot_time}\n"
                f"Часовой пояс: {timezone_name}\n\n"
                "Вы можете выбрать другое доступное время в боте."
            ),
            notification_type="appointment_cancelled_by_coach",
            related_entity_type="availability_slot",
            related_entity_id=slot_id,
        )

    if notification_sent is not None and notification_sent.ok:
        await callback.message.edit_text("Занятие отменено. Клиенту отправлено уведомление.")
    else:
        await callback.message.edit_text(
            "Занятие отменено, но уведомление клиенту отправить не удалось."
        )

@router.callback_query(F.data == "schedule:ics")
async def download_coach_future_bookings_ics_handler(callback: CallbackQuery) -> None:
    result = await build_coach_future_bookings_ics(
        telegram_id=callback.from_user.id,
    )

    await callback.answer()

    if not result.ok or result.file_bytes is None or result.filename is None:
        await callback.message.answer("Нет будущих занятий для календаря.")
        return

    await callback.message.answer_document(
        BufferedInputFile(
            result.file_bytes,
            filename=result.filename,
        ),
        caption="Файл календаря с будущими занятиями.",
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
        await callback.message.answer("Не удалось подготовить файл календаря.")
        return

    await callback.message.answer_document(
        BufferedInputFile(
            result.file_bytes,
            filename=result.filename,
        ),
        caption="Файл календаря для этого занятия.",
    )
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.schedule import (
    available_slot_management_keyboard,
    booked_slot_management_keyboard,
    coach_schedule_keyboard,
    coach_slots_keyboard,
    confirm_cancel_booked_slot_keyboard,
    slot_duration_keyboard,
)

from app.services.schedule_management import (
    cancel_booked_slot_for_coach,
    delete_available_slot_for_coach,
    get_slot_card_for_coach,
    list_coach_manageable_slots,
)
from app.bot.states.schedule import ScheduleStates
from app.services.schedule import (
    create_availability_slot,
    get_coach_by_telegram_id,
    list_coach_slots,
    parse_coach_datetime,
)
from app.utils.datetime import format_slot_range_for_timezone, ensure_utc, format_dt_for_timezone

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
        "Введите дату слота в формате YYYY-MM-DD.\n\n"
        "Например: 2026-05-10"
    )

    await callback.answer()


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
            "Неверный формат даты.\n\n"
            "Введите дату в формате YYYY-MM-DD. Например: 2026-05-10"
        )
        return

    await state.update_data(slot_date=date_text)
    await state.set_state(ScheduleStates.waiting_for_slot_start_time)

    await message.answer(
        "Введите время начала в формате HH:MM.\n\n"
        "Например: 14:30"
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
            "Неверный формат времени.\n\n"
            "Введите время в формате HH:MM. Например: 14:30"
        )
        return

    await state.update_data(slot_start_time=time_text)
    await state.set_state(ScheduleStates.waiting_for_slot_duration)

    await message.answer(
        "Выберите длительность слота:",
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
        await callback.message.edit_text(
            "У вас пока нет будущих активных слотов."
        )
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
        await callback.message.edit_text(
            "Слот не найден или у вас нет доступа."
        )
        return

    slot = card.slot

    slot_time = format_slot_range_for_timezone(
        slot.starts_at,
        slot.ends_at,
        timezone_name,
    )
    if slot.status == "available":
        text = (
            "Карточка слота\n\n"
            f"Время: {slot_time}\n"
            f"Часовой пояс: {timezone_name}\n"
            "Статус: свободен"
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
            f"Время: {slot.starts_at} — {slot.ends_at}\n"
            "Статус: занят\n"
            f"Клиент: {client_name}"
        )

        await callback.message.edit_text(
            text,
            reply_markup=booked_slot_management_keyboard(slot.id),
        )
        return

    await callback.message.edit_text(
        "Этот слот уже отменен."
    )

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
            "Слот удален.\n\n"
            "У вас больше нет будущих активных слотов."
        )
        return

    await callback.message.edit_text(
        "Слот удален.\n\n"
        "Ваши будущие слоты:",
        reply_markup=coach_slots_keyboard(slots),
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
        await callback.message.edit_text(
            "Слот не найден или уже не является занятым."
        )
        return

    client_name = "неизвестный клиент"

    if card.client is not None:
        client_name = card.client.display_name or "без имени"

    await callback.message.edit_text(
        "Отменить занятие?\n\n"
        f"Клиент: {client_name}\n"
        f"Время: {card.slot.starts_at} — {card.slot.ends_at}\n\n"
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
        await callback.message.edit_text(
            "Не удалось отменить занятие. Возможно, оно уже отменено."
        )
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

    notification_sent = False

    if result.client_telegram_id is not None:
        try:
            await callback.bot.send_message(
                chat_id=result.client_telegram_id,
                text=(
                    "Ваше занятие отменено тренером.\n\n"
                    f"Время: {slot_time}\n"
                    f"Часовой пояс: {timezone_name}\n\n"
                    "Вы можете выбрать другое доступное время в боте."
                ),
            )
            notification_sent = True
        except Exception:
            notification_sent = False

    if notification_sent:
        await callback.message.edit_text(
            "Занятие отменено. Клиенту отправлено уведомление."
        )
    else:
        await callback.message.edit_text(
            "Занятие отменено, но уведомление клиенту отправить не удалось."
        )
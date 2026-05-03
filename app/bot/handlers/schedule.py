from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.schedule import coach_schedule_keyboard, slot_duration_keyboard
from app.bot.states.schedule import ScheduleStates
from app.services.schedule import (
    create_availability_slot,
    get_coach_by_telegram_id,
    list_coach_slots,
    parse_coach_datetime,
)

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

    slots = await list_coach_slots(coach_id=coach.id, limit=10)

    await callback.answer()

    if not slots:
        await callback.message.answer("У вас пока нет созданных слотов.")
        return

    lines = ["Ближайшие слоты:\n"]

    for slot in slots:
        lines.append(
            f"• {slot.starts_at} — {slot.ends_at} | {slot.status}"
        )

    await callback.message.answer("\n".join(lines))
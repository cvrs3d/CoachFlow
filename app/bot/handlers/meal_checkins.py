from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.formatters.meal_checkins import format_meal_checkin_schedules_text
from app.bot.keyboards.meal_checkins import meal_checkin_schedule_keyboard
from app.bot.utils.safe_messages import safe_answer_or_edit_text
from app.services.meal_checkins import (
    ensure_default_meal_checkin_schedules_for_coach,
    generate_meal_checkins_for_coach_date,
    list_meal_checkin_schedules_for_coach,
)

router = Router()


@router.message(F.text == "🍽 Расписание питания")
async def meal_checkin_schedule_menu_handler(message: Message) -> None:
    result = await list_meal_checkin_schedules_for_coach(
        coach_telegram_id=message.from_user.id,
    )

    if not result.ok:
        await message.answer("Раздел доступен только активному тренеру.")
        return

    await message.answer(
        format_meal_checkin_schedules_text(result),
        reply_markup=meal_checkin_schedule_keyboard(),
    )


@router.callback_query(F.data == "mcs:create_default")
async def create_default_meal_checkin_schedule_handler(callback: CallbackQuery) -> None:
    result = await ensure_default_meal_checkin_schedules_for_coach(
        coach_telegram_id=callback.from_user.id,
    )

    await callback.answer()

    if not result.ok:
        await callback.message.answer("Не удалось создать расписание питания.")
        return

    schedules_result = await list_meal_checkin_schedules_for_coach(
        coach_telegram_id=callback.from_user.id,
    )

    await safe_answer_or_edit_text(
        callback.message,
        "Дефолтное расписание питания создано.\n\n"
        f"Создано новых записей: {result.created_count}\n\n"
        f"{format_meal_checkin_schedules_text(schedules_result)}",
        reply_markup=meal_checkin_schedule_keyboard(),
    )


@router.callback_query(F.data == "mcs:generate_today")
async def generate_today_meal_checkins_handler(callback: CallbackQuery) -> None:
    result = await generate_meal_checkins_for_coach_date(
        coach_telegram_id=callback.from_user.id,
        target_date=datetime.now(timezone.utc),
    )

    await callback.answer()

    if not result.ok:
        await callback.message.answer("Не удалось сгенерировать check-ins на сегодня.")
        return

    await callback.message.answer(
        "Check-ins на сегодня сгенерированы.\n\n"
        f"Создано новых check-ins: {result.created_count}"
    )


@router.callback_query(F.data == "mcs:generate_tomorrow")
async def generate_tomorrow_meal_checkins_handler(callback: CallbackQuery) -> None:
    result = await generate_meal_checkins_for_coach_date(
        coach_telegram_id=callback.from_user.id,
        target_date=datetime.now(timezone.utc) + timedelta(days=1),
    )

    await callback.answer()

    if not result.ok:
        await callback.message.answer("Не удалось сгенерировать check-ins на завтра.")
        return

    await callback.message.answer(
        "Check-ins на завтра сгенерированы.\n\n"
        f"Создано новых check-ins: {result.created_count}"
    )
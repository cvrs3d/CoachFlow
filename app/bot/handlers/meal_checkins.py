from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.menu import MainMenuCallback
from app.bot.i18n import get_user_language, t
from app.bot.formatters.meal_checkins import format_meal_checkin_schedules_text
from app.bot.keyboards.meal_checkins import meal_checkin_schedule_keyboard
from app.bot.utils.safe_messages import safe_answer_or_edit_text
from app.services.meal_checkins import (
    ensure_default_meal_checkin_schedules_for_coach,
    generate_meal_checkins_for_coach_date,
    list_meal_checkin_schedules_for_coach,
)

router = Router()


@router.callback_query(MainMenuCallback.filter(F.action == "coach_meal_schedule"))
async def meal_checkin_schedule_menu_handler(callback: CallbackQuery) -> None:
    await callback.answer()
    language_code = await get_user_language(callback.from_user.id)
    result = await list_meal_checkin_schedules_for_coach(
        coach_telegram_id=callback.from_user.id,
    )

    if not result.ok:
        await callback.message.answer(t("meal_checkins.access_denied", language_code))
        return

    await callback.message.answer(
        format_meal_checkin_schedules_text(result),
        reply_markup=meal_checkin_schedule_keyboard(),
    )


@router.callback_query(F.data == "mcs:create_default")
async def create_default_meal_checkin_schedule_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    result = await ensure_default_meal_checkin_schedules_for_coach(
        coach_telegram_id=callback.from_user.id,
    )

    await callback.answer()

    if not result.ok:
        await callback.message.answer(t("meal_checkins.create_failed", language_code))
        return

    schedules_result = await list_meal_checkin_schedules_for_coach(
        coach_telegram_id=callback.from_user.id,
    )

    await safe_answer_or_edit_text(
        callback.message,
        t(
            "meal_checkins.created",
            language_code,
            count=result.created_count,
            schedule_text=format_meal_checkin_schedules_text(schedules_result),
        ),
        reply_markup=meal_checkin_schedule_keyboard(),
    )


@router.callback_query(F.data == "mcs:generate_today")
async def generate_today_meal_checkins_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    result = await generate_meal_checkins_for_coach_date(
        coach_telegram_id=callback.from_user.id,
        target_date=datetime.now(timezone.utc),
    )

    await callback.answer()

    if not result.ok:
        await callback.message.answer(t("meal_checkins.generate_today_failed", language_code))
        return

    await callback.message.answer(
        t("meal_checkins.today_generated", language_code, count=result.created_count)
    )


@router.callback_query(F.data == "mcs:generate_tomorrow")
async def generate_tomorrow_meal_checkins_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    result = await generate_meal_checkins_for_coach_date(
        coach_telegram_id=callback.from_user.id,
        target_date=datetime.now(timezone.utc) + timedelta(days=1),
    )

    await callback.answer()

    if not result.ok:
        await callback.message.answer(t("meal_checkins.generate_tomorrow_failed", language_code))
        return

    await callback.message.answer(
        t("meal_checkins.tomorrow_generated", language_code, count=result.created_count)
    )
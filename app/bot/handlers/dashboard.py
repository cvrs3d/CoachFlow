from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.i18n import get_user_language, t
from app.services.dashboard import get_coach_dashboard
from app.bot.callbacks.menu import MainMenuCallback

router = Router()


@router.callback_query(MainMenuCallback.filter(F.action == "coach_dashboard"))
async def coach_dashboard_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    result = await get_coach_dashboard(
        telegram_id=callback.from_user.id,
    )

    await callback.answer()

    if not result.ok or result.stats is None:
        await callback.message.answer(t("dashboard.access_denied", language_code))
        return

    stats = result.stats

    text = (
        t("dashboard.title", language_code)
        + f"\n\n🌍 Часовой пояс: {result.timezone_name}\n\n"
        + t("dashboard.today", language_code)
        + "\n"
        + t("dashboard.trainings", language_code, count=stats.today_appointments_count)
        + "\n"
        + t("dashboard.new_reports", language_code, count=stats.today_new_meal_reports_count)
        + "\n"
        + t("dashboard.pending_reviews", language_code, count=stats.pending_meal_reports_count)
        + "\n"
        + t("dashboard.waiting_clarification", language_code, count=stats.waiting_clarification_count)
        + "\n\n"
        + t("dashboard.last_7_days", language_code)
        + "\n"
        + t("dashboard.sent_reports", language_code, count=stats.reports_7d_count)
        + "\n"
        + t("dashboard.reviewed", language_code, count=stats.reviewed_7d_count)
        + "\n"
        + t("dashboard.needs_improvement", language_code, count=stats.needs_improvement_7d_count)
        + "\n\n"
        + t("dashboard.clients", language_code)
        + "\n"
        + t("dashboard.active_clients", language_code, count=stats.active_clients_count)
    )

    await callback.message.answer(text)

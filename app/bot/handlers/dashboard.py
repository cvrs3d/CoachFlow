from aiogram import F, Router
from aiogram.types import Message

from app.services.dashboard import get_coach_dashboard

router = Router()


@router.message(F.text == "📊 Обзор")
async def coach_dashboard_handler(message: Message) -> None:
    result = await get_coach_dashboard(
        telegram_id=message.from_user.id,
    )

    if not result.ok or result.stats is None:
        await message.answer("Обзор доступен только активному тренеру.")
        return

    stats = result.stats

    text = (
        "📊 Обзор тренера\n\n"
        f"🌍 Часовой пояс: {result.timezone_name}\n\n"
        "📅 Сегодня:\n"
        f"🏋️ Занятий: {stats.today_appointments_count}\n"
        f"🍽 Новых food reports: {stats.today_new_meal_reports_count}\n"
        f"📝 Отчетов на проверку: {stats.pending_meal_reports_count}\n"
        f"❓ Уточнений ожидают ответа клиента: {stats.waiting_clarification_count}\n\n"
        "📈 За 7 дней:\n"
        f"📤 Отчетов отправлено: {stats.reports_7d_count}\n"
        f"✅ Проверено: {stats.reviewed_7d_count}\n"
        f"⚠️ Needs improvement: {stats.needs_improvement_7d_count}\n\n"
        "👥 Клиенты:\n"
        f"🟢 Активных клиентов: {stats.active_clients_count}"
    )

    await message.answer(text)
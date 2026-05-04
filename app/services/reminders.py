from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import select

from app.db.database import AsyncSessionLocal, safe_commit
from app.db.models import Appointment, AvailabilitySlot, Client, Coach, User


async def send_appointment_24h_reminders(bot: Bot) -> None:
    """
    Ищет занятия, которые начнутся примерно через 24 часа,
    отправляет клиенту уведомление и помечает appointment как обработанный.

    Окно 23:50–24:10 нужно, чтобы задача могла запускаться раз в 10 минут.
    """

    now = datetime.now(timezone.utc)
    window_start = now + timedelta(hours=23, minutes=50)
    window_end = now + timedelta(hours=24, minutes=10)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Appointment, AvailabilitySlot, Client, Coach, User)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .join(Client, Appointment.client_id == Client.id)
            .join(Coach, Appointment.coach_id == Coach.id)
            .join(User, Client.user_id == User.id)
            .where(Appointment.status == "booked")
            .where(Appointment.reminder_24h_sent_at.is_(None))
            .where(AvailabilitySlot.starts_at >= window_start)
            .where(AvailabilitySlot.starts_at < window_end)
        )

        rows = result.all()

        for appointment, slot, client, coach, user in rows:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "Напоминание о занятии.\n\n"
                        f"Занятие состоится завтра:\n"
                        f"{slot.starts_at}\n\n"
                        "Если не сможете прийти, свяжитесь с тренером заранее."
                    ),
                )

                appointment.reminder_24h_sent_at = datetime.now(timezone.utc)

            except Exception:
                # Пока просто пропускаем. Позже добавим логирование в таблицу notifications/job_execution_logs.
                continue

        await from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Appointment, AvailabilitySlot, Client, Coach, User


async def send_appointment_24h_reminders(bot: Bot) -> None:
    """
    Ищет занятия, которые начнутся примерно через 24 часа,
    отправляет клиенту уведомление и помечает appointment как обработанный.

    Окно 23:50–24:10 нужно, чтобы задача могла запускаться раз в 10 минут.
    """

    now = datetime.now(timezone.utc)
    window_start = now + timedelta(hours=23, minutes=50)
    window_end = now + timedelta(hours=24, minutes=10)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Appointment, AvailabilitySlot, Client, Coach, User)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .join(Client, Appointment.client_id == Client.id)
            .join(Coach, Appointment.coach_id == Coach.id)
            .join(User, Client.user_id == User.id)
            .where(Appointment.status == "booked")
            .where(Appointment.reminder_24h_sent_at.is_(None))
            .where(AvailabilitySlot.starts_at >= window_start)
            .where(AvailabilitySlot.starts_at < window_end)
        )

        rows = result.all()

        for appointment, slot, client, coach, user in rows:
            try:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "Напоминание о занятии.\n\n"
                        f"Занятие состоится завтра:\n"
                        f"{slot.starts_at}\n\n"
                        "Если не сможете прийти, свяжитесь с тренером заранее."
                    ),
                )

                appointment.reminder_24h_sent_at = datetime.now(timezone.utc)

            except Exception:
                # Пока просто пропускаем. Позже добавим логирование в таблицу notifications/job_execution_logs.
                continue

        await safe_commit(session)
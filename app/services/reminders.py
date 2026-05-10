from datetime import datetime, timedelta, timezone

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.db.database import AsyncSessionLocal, safe_commit
from app.db.models import Appointment, AvailabilitySlot, Client, Coach, User

from app.utils.datetime import format_slot_range_for_timezone

from app.services.notifications import send_logged_message, SendNotificationResult

import logging

logger = logging.getLogger(__name__)

async def send_appointment_24h_reminders(
    bot: Bot,
    session_factory=AsyncSessionLocal,
) -> None:
    """
    Ищет занятия, которые начнутся примерно через 24 часа,
    отправляет клиенту уведомление и помечает appointment как обработанный.

    Окно 23:50–24:10 нужно, чтобы задача могла запускаться раз в 10 минут.
    """

    now = datetime.now(timezone.utc)
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=25)
    # -----------------TEST------------------ # 
    # window_start = now + timedelta(minutes=1)
    # window_end = now + timedelta(minutes=5)

    ClientUser = aliased(User)
    CoachUser = aliased(User)

    async with session_factory() as session:
        result = await session.execute(
            select(
                Appointment,
                AvailabilitySlot,
                Client,
                Coach,
                ClientUser,
                CoachUser,
            )
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .join(Client, Appointment.client_id == Client.id)
            .join(Coach, Appointment.coach_id == Coach.id)
            .join(ClientUser, Client.user_id == ClientUser.id)
            .join(CoachUser, Coach.user_id == CoachUser.id)
            .where(Appointment.status == "booked")
            .where(Appointment.reminder_24h_sent_at.is_(None))
            .where(AvailabilitySlot.starts_at >= window_start)
            .where(AvailabilitySlot.starts_at < window_end)
        )

        logger.info("24h reminders job started at %s", now.isoformat())

        rows = result.all()

        logger.info(
            "24h reminders found rows=%s window_start=%s window_end=%s",
            len(rows),
            window_start.isoformat(),
            window_end.isoformat(),
        )


        for appointment, slot, client, coach, client_user, coach_user in rows:
            client_sent = False
            coach_sent = False

            slot_time = format_slot_range_for_timezone(
            starts_at = slot.starts_at,
            ends_at = slot.ends_at,
            timezone_name = coach.timezone)

            notification_client_result = await send_logged_message (
                bot=bot,
                chat_id=client_user.telegram_id,
                text=(
                    f"Напоминание о занятии с {'тренером' + coach.display_name or 'тренером'}.\n\n"
                    f"Занятие состоится завтра:\n"
                    f"{slot_time}\n\n"
                    "Если не сможете прийти, свяжитесь с тренером заранее."
                ),
                notification_type="appointment_reminder_24h_client",
                related_entity_type="appointment",
                related_entity_id=appointment.id,
                session_factory=session_factory,
            )
            if notification_client_result and notification_client_result.ok:
                client_sent = True
            else:
                logger.info(
                    "Failed to send 24h reminder to client",
                    extra={
                        "appointment_id": appointment.id,
                        "client_user_id": client_user.id,
                        "telegram_id": client_user.telegram_id,
                    },
                )

            notification_coach_result = await send_logged_message (
                bot=bot,
                chat_id=coach_user.telegram_id,
                text=(
                    "Напоминание о занятии с клиентом.\n\n"
                    f"Клиент: {client.display_name or 'без имени'}\n"
                    f"Время: {slot_time}\n\n"
                    "Уведомление отправлено за день до занятия."
                ),
                notification_type="appointment_reminder_24h_coach",
                related_entity_type="appointment",
                related_entity_id=appointment.id,
                session_factory=session_factory,
            )
            if notification_coach_result and notification_coach_result.ok:
                coach_sent = True
            else:
                logger.info(
                    "Failed to send 24h reminder to client",
                    extra={
                        "appointment_id": appointment.id,
                        "coach_user_id": coach_user.id,
                        "telegram_id": coach_user.telegram_id,
                    },
                )

            if client_sent or coach_sent:
                appointment.reminder_24h_sent_at = datetime.now(timezone.utc)

        await safe_commit(session)
import uuid
from dataclasses import dataclass

from aiogram import Bot

from app.db.database import AsyncSessionLocal
from app.db.models import NotificationLog


@dataclass
class SendNotificationResult:
    ok: bool
    error_message: str | None = None

# appointment_booked
# appointment_cancelled_by_client
# appointment_cancelled_by_coach
# appointment_reminder_24h_client
# appointment_reminder_24h_coach
# meal_report_submitted
# meal_report_reviewed
# clarification_requested
# clarification_answered


async def create_notification_log(
    *,
    recipient_telegram_id: int,
    notification_type: str,
    status: str,
    error_message: str | None = None,
    related_entity_type: str | None = None,
    related_entity_id: str | None = None,
    session_factory=AsyncSessionLocal,
) -> None:
    async with session_factory() as session:
        log = NotificationLog(
            id=str(uuid.uuid4()),
            recipient_telegram_id=recipient_telegram_id,
            notification_type=notification_type,
            status=status,
            error_message=error_message,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )

        session.add(log)
        await session.commit()


async def send_logged_message(
    *,
    bot: Bot,
    chat_id: int,
    text: str,
    notification_type: str,
    related_entity_type: str | None = None,
    related_entity_id: str | None = None,
    session_factory=AsyncSessionLocal,
) -> SendNotificationResult:
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
        )

    except Exception as error:
        error_message = str(error)

        await create_notification_log(
            recipient_telegram_id=chat_id,
            notification_type=notification_type,
            status="failed",
            error_message=error_message,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            session_factory=session_factory,
        )

        return SendNotificationResult(
            ok=False,
            error_message=error_message,
        )

    await create_notification_log(
        recipient_telegram_id=chat_id,
        notification_type=notification_type,
        status="sent",
        error_message=None,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        session_factory=session_factory,
    )

    return SendNotificationResult(ok=True)
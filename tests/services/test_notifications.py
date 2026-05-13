from unittest.mock import AsyncMock

from sqlalchemy import select

from app.db.models import NotificationLog
from app.services.notifications import send_logged_message


async def test_send_logged_message_writes_sent_log(session_factory):
    bot = AsyncMock()
    bot.send_message = AsyncMock()

    result = await send_logged_message(
        bot=bot,
        chat_id=123456,
        text="Hello",
        notification_type="test_notification",
        related_entity_type="test_entity",
        related_entity_id="entity-1",
        session_factory=session_factory,
    )

    assert result.ok is True

    bot.send_message.assert_awaited_once_with(
        chat_id=123456,
        text="Hello",
    )

    async with session_factory() as session:
        logs_result = await session.execute(select(NotificationLog))
        logs = logs_result.scalars().all()

        assert len(logs) == 1
        assert logs[0].recipient_telegram_id == 123456
        assert logs[0].notification_type == "test_notification"
        assert logs[0].status == "sent"
        assert logs[0].error_message is None
        assert logs[0].related_entity_type == "test_entity"
        assert logs[0].related_entity_id == "entity-1"


async def test_send_logged_message_writes_failed_log(session_factory):
    bot = AsyncMock()
    bot.send_message = AsyncMock(side_effect=RuntimeError("telegram failed"))

    result = await send_logged_message(
        bot=bot,
        chat_id=123456,
        text="Hello",
        notification_type="test_notification",
        related_entity_type="test_entity",
        related_entity_id="entity-1",
        session_factory=session_factory,
    )

    assert result.ok is False
    assert "telegram failed" in (result.error_message or "")

    async with session_factory() as session:
        logs_result = await session.execute(select(NotificationLog))
        logs = logs_result.scalars().all()

        assert len(logs) == 1
        assert logs[0].recipient_telegram_id == 123456
        assert logs[0].notification_type == "test_notification"
        assert logs[0].status == "failed"
        assert "telegram failed" in (logs[0].error_message or "")

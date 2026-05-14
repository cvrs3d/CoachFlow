from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.db.models import MealCheckin, MealCheckinSchedule, NotificationLog
from app.services.meal_checkins import (
    ensure_default_meal_checkin_schedules_for_coach,
    generate_meal_checkins_for_coach_date,
)
from tests.factories.entities import create_client_for_coach, create_coach
from unittest.mock import AsyncMock
from app.services.meal_checkins import send_due_meal_checkin_requests

async def test_coach_can_create_default_meal_checkin_schedules(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        await session.commit()

    result = await ensure_default_meal_checkin_schedules_for_coach(
        coach_telegram_id=1001,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.created_count == 3

    async with session_factory() as session:
        schedules_result = await session.execute(select(MealCheckinSchedule))
        schedules = schedules_result.scalars().all()

        assert len(schedules) == 3
        assert {schedule.meal_type for schedule in schedules} == {
            "breakfast",
            "lunch",
            "dinner",
        }
        assert {schedule.local_time for schedule in schedules} == {
            "09:00",
            "13:00",
            "19:00",
        }


async def test_default_meal_checkin_schedules_are_idempotent(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        await session.commit()

    first = await ensure_default_meal_checkin_schedules_for_coach(
        coach_telegram_id=1001,
        session_factory=session_factory,
    )

    second = await ensure_default_meal_checkin_schedules_for_coach(
        coach_telegram_id=1001,
        session_factory=session_factory,
    )

    assert first.ok is True
    assert first.created_count == 3
    assert second.ok is True
    assert second.created_count == 0


async def test_generate_meal_checkins_for_active_clients(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    schedules = await ensure_default_meal_checkin_schedules_for_coach(
        coach_telegram_id=1001,
        session_factory=session_factory,
    )

    assert schedules.ok is True

    result = await generate_meal_checkins_for_coach_date(
        coach_telegram_id=1001,
        target_date=datetime.now(timezone.utc),
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.created_count == 3

    async with session_factory() as session:
        checkins_result = await session.execute(select(MealCheckin))
        checkins = checkins_result.scalars().all()

        assert len(checkins) == 3
        assert {checkin.status for checkin in checkins} == {"pending"}
        assert {checkin.meal_type for checkin in checkins} == {
            "breakfast",
            "lunch",
            "dinner",
        }


async def test_generate_meal_checkins_is_idempotent(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    await ensure_default_meal_checkin_schedules_for_coach(
        coach_telegram_id=1001,
        session_factory=session_factory,
    )

    first = await generate_meal_checkins_for_coach_date(
        coach_telegram_id=1001,
        target_date=datetime.now(timezone.utc),
        session_factory=session_factory,
    )

    second = await generate_meal_checkins_for_coach_date(
        coach_telegram_id=1001,
        target_date=datetime.now(timezone.utc),
        session_factory=session_factory,
    )

    assert first.ok is True
    assert first.created_count == 3
    assert second.ok is True
    assert second.created_count == 0

async def test_send_due_meal_checkin_requests_marks_checkin_as_sent(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )

        checkin = MealCheckin(
            id="checkin-1",
            client_id=client.id,
            coach_id=coach.id,
            meal_type="lunch",
            scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            status="pending",
        )
        session.add(checkin)

        await session.commit()

    bot = AsyncMock()
    bot.send_message = AsyncMock()

    result = await send_due_meal_checkin_requests(
        bot=bot,
        session_factory=session_factory,
    )

    assert result.sent_count == 1
    assert result.failed_count == 0

    bot.send_message.assert_awaited_once()

    async with session_factory() as session:
        checkin_result = await session.execute(
            select(MealCheckin).where(MealCheckin.id == "checkin-1")
        )
        checkin = checkin_result.scalar_one()

        assert checkin.status == "sent"

        logs_result = await session.execute(select(NotificationLog))
        logs = logs_result.scalars().all()

        assert len(logs) == 1
        assert logs[0].notification_type == "meal_checkin_request"
        assert logs[0].status == "sent"
        assert logs[0].related_entity_type == "meal_checkin"
        assert logs[0].related_entity_id == "checkin-1"

async def test_send_due_meal_checkin_requests_skips_future_checkins(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )

        checkin = MealCheckin(
            id="checkin-future",
            client_id=client.id,
            coach_id=coach.id,
            meal_type="dinner",
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1),
            status="pending",
        )
        session.add(checkin)

        await session.commit()

    bot = AsyncMock()
    bot.send_message = AsyncMock()

    result = await send_due_meal_checkin_requests(
        bot=bot,
        session_factory=session_factory,
    )

    assert result.sent_count == 0
    assert result.failed_count == 0

    bot.send_message.assert_not_awaited()

    async with session_factory() as session:
        checkin_result = await session.execute(
            select(MealCheckin).where(MealCheckin.id == "checkin-future")
        )
        checkin = checkin_result.scalar_one()

        assert checkin.status == "pending"

async def test_send_due_meal_checkin_requests_logs_failed_notification(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )

        checkin = MealCheckin(
            id="checkin-failed",
            client_id=client.id,
            coach_id=coach.id,
            meal_type="breakfast",
            scheduled_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            status="pending",
        )
        session.add(checkin)

        await session.commit()

    bot = AsyncMock()
    bot.send_message = AsyncMock(side_effect=RuntimeError("telegram failed"))

    result = await send_due_meal_checkin_requests(
        bot=bot,
        session_factory=session_factory,
    )

    assert result.sent_count == 0
    assert result.failed_count == 1

    async with session_factory() as session:
        checkin_result = await session.execute(
            select(MealCheckin).where(MealCheckin.id == "checkin-failed")
        )
        checkin = checkin_result.scalar_one()

        assert checkin.status == "pending"

        logs_result = await session.execute(select(NotificationLog))
        logs = logs_result.scalars().all()

        assert len(logs) == 1
        assert logs[0].status == "failed"
        assert logs[0].notification_type == "meal_checkin_request"
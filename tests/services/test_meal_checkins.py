from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import MealCheckin, MealCheckinSchedule
from app.services.meal_checkins import (
    ensure_default_meal_checkin_schedules_for_coach,
    generate_meal_checkins_for_coach_date,
)
from tests.factories.entities import create_client_for_coach, create_coach


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
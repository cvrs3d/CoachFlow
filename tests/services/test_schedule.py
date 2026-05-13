from datetime import UTC, datetime

from app.services.schedule import create_availability_slot
from tests.factories.entities import create_coach


async def test_coach_cannot_create_overlapping_slots(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        await session.commit()

        coach_id = coach.id

    starts_at = datetime(2026, 5, 20, 12, 0, tzinfo=UTC)

    first = await create_availability_slot(
        coach_id=coach_id,
        starts_at=starts_at,
        duration_minutes=60,
        session_factory=session_factory,
    )

    second = await create_availability_slot(
        coach_id=coach_id,
        starts_at=datetime(2026, 5, 20, 12, 30, tzinfo=UTC),
        duration_minutes=60,
        session_factory=session_factory,
    )

    assert first.ok is True
    assert second.ok is False
    assert second.reason == "overlap"

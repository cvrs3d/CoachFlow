import uuid
from datetime import datetime, timedelta, timezone

from app.db.models import (
    Client,
    ClientCoachRelation,
    Coach,
    User,
    AvailabilitySlot,
)


async def create_user(
    session,
    *,
    telegram_id: int,
    role: str,
    status: str = "active",
    username: str | None = None,
):
    user = User(
        id=str(uuid.uuid4()),
        telegram_id=telegram_id,
        username=username,
        role=role,
        status=status,
    )
    session.add(user)
    await session.flush()
    return user


async def create_coach(
    session,
    *,
    telegram_id: int = 1001,
    timezone_name: str = "Europe/Prague",
):
    user = await create_user(
        session,
        telegram_id=telegram_id,
        role="coach",
        status="active",
        username="coach",
    )

    coach = Coach(
        id=str(uuid.uuid4()),
        user_id=user.id,
        display_name="Test Coach",
        timezone=timezone_name,
    )
    session.add(coach)
    await session.flush()

    return user, coach


async def create_client_for_coach(
    session,
    *,
    coach,
    telegram_id: int = 2001,
    display_name: str = "Test Client",
):
    user = await create_user(
        session,
        telegram_id=telegram_id,
        role="client",
        status="active",
        username="client",
    )

    client = Client(
        id=str(uuid.uuid4()),
        user_id=user.id,
        display_name=display_name,
        status="active",
    )
    session.add(client)
    await session.flush()

    relation = ClientCoachRelation(
        id=str(uuid.uuid4()),
        client_id=client.id,
        coach_id=coach.id,
        status="active",
    )
    session.add(relation)
    await session.flush()

    return user, client, relation


async def create_available_slot(
    session,
    *,
    coach,
    starts_in_hours: int = 48,
    duration_minutes: int = 60,
):
    starts_at = datetime.now(timezone.utc) + timedelta(hours=starts_in_hours)
    ends_at = starts_at + timedelta(minutes=duration_minutes)

    slot = AvailabilitySlot(
        id=str(uuid.uuid4()),
        coach_id=coach.id,
        starts_at=starts_at,
        ends_at=ends_at,
        status="available",
    )
    session.add(slot)
    await session.flush()

    return slot
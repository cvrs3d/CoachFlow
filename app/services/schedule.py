import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db.database import AsyncSessionLocal, safe_commit
from app.db.models import (
    AvailabilitySlot,
    Coach,
    User,
)


@dataclass
class CreateSlotResult:
    ok: bool
    reason: str | None = None
    slot_id: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


async def get_coach_by_telegram_id(
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> Coach | None:
    async with session_factory() as session:
        result = await session.execute(
            select(Coach)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )

        return result.scalar_one_or_none()


def parse_coach_datetime(
    *,
    date_text: str,
    time_text: str,
    timezone_name: str,
) -> datetime:
    """
    date_text: '2026-05-10'
    time_text: '14:30'
    timezone_name: 'Europe/Prague'
    """
    naive = datetime.strptime(
        f"{date_text} {time_text}",
        "%Y-%m-%d %H:%M",
    )

    return naive.replace(tzinfo=ZoneInfo(timezone_name))


async def create_availability_slot(
    *,
    coach_id: str,
    starts_at: datetime,
    duration_minutes: int,
    session_factory=AsyncSessionLocal,
) -> CreateSlotResult:
    starts_at = starts_at.astimezone(UTC)
    ends_at = starts_at + timedelta(minutes=duration_minutes)

    async with session_factory() as session:
        async with session.begin():
            try:
                # Проверка пересечения:
                # существующий starts_at < новый ends_at
                # существующий ends_at > новый starts_at
                conflict_result = await session.execute(
                    select(AvailabilitySlot)
                    .where(AvailabilitySlot.coach_id == coach_id)
                    .where(
                        AvailabilitySlot.status not in ["cancelled_by_client", "cancelled_by_coach"]
                    )
                    .where(AvailabilitySlot.starts_at < ends_at)
                    .where(AvailabilitySlot.ends_at > starts_at)
                    .limit(1)
                )

                conflict = conflict_result.scalar_one_or_none()

                if conflict is not None:
                    await session.rollback()
                    return CreateSlotResult(
                        ok=False,
                        reason="overlap",
                    )

                slot = AvailabilitySlot(
                    id=str(uuid.uuid4()),
                    coach_id=coach_id,
                    starts_at=starts_at,
                    ends_at=ends_at,
                    status="available",
                )

                session.add(slot)
                await safe_commit(session)

                return CreateSlotResult(
                    ok=True,
                    slot_id=slot.id,
                    starts_at=starts_at,
                    ends_at=ends_at,
                )

            except Exception:
                await session.rollback()
                raise


async def list_coach_slots(
    *,
    coach_id: str,
    limit: int = 10,
    session_factory=AsyncSessionLocal,
) -> list[AvailabilitySlot]:
    async with session_factory() as session:
        result = await session.execute(
            select(AvailabilitySlot)
            .where(AvailabilitySlot.coach_id == coach_id)
            .where(AvailabilitySlot.status != "cancelled")
            .order_by(AvailabilitySlot.starts_at.asc())
            .limit(limit)
        )

        return list(result.scalars().all())

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, text

from app.services.invites import get_coach_by_telegram_id

from app.db.database import AsyncSessionLocal, safe_commit
from app.db.models import (
    Appointment,
    AvailabilitySlot,
    Client,
    Coach,
    User,
)


@dataclass
class CoachSlotCard:
    slot: AvailabilitySlot
    appointment: Appointment | None = None
    client: Client | None = None
    client_user: User | None = None


@dataclass
class CancelBookedSlotResult:
    ok: bool
    reason: str | None = None
    client_telegram_id: int | None = None
    client_display_name: str | None = None
    starts_at: str | None = None
    ends_at: str | None = None



async def list_coach_manageable_slots(
    *,
    telegram_id: int,
    limit: int = 20,
    session_factory=AsyncSessionLocal,
) -> list[AvailabilitySlot]:
    coach = await get_coach_by_telegram_id(telegram_id)

    if coach is None:
        return []

    async with session_factory() as session:
        result = await session.execute(
            select(AvailabilitySlot)
            .where(AvailabilitySlot.coach_id == coach.id)
            .where(AvailabilitySlot.status.in_(["available", "booked"]))
            .where(AvailabilitySlot.starts_at >= datetime.now(timezone.utc))
            .order_by(AvailabilitySlot.starts_at.asc())
            .limit(limit)
        )

        return list(result.scalars().all())


async def get_slot_card_for_coach(
    *,
    telegram_id: int,
    slot_id: str,
    session_factory=AsyncSessionLocal,
) -> CoachSlotCard | None:
    coach = await get_coach_by_telegram_id(telegram_id)

    if coach is None:
        return None

    async with session_factory() as session:
        slot_result = await session.execute(
            select(AvailabilitySlot)
            .where(AvailabilitySlot.id == slot_id)
            .where(AvailabilitySlot.coach_id == coach.id)
        )
        slot = slot_result.scalar_one_or_none()

        if slot is None:
            return None

        if slot.status != "booked":
            return CoachSlotCard(slot=slot)

        appointment_result = await session.execute(
            select(Appointment, Client, User)
            .join(Client, Appointment.client_id == Client.id)
            .join(User, Client.user_id == User.id)
            .where(Appointment.slot_id == slot.id)
            .where(Appointment.coach_id == coach.id)
            .where(Appointment.status == "booked")
        )

        row = appointment_result.one_or_none()

        if row is None:
            return CoachSlotCard(slot=slot)

        appointment, client, client_user = row

        return CoachSlotCard(
            slot=slot,
            appointment=appointment,
            client=client,
            client_user=client_user,
        )


async def delete_available_slot_for_coach(
    *,
    telegram_id: int,
    slot_id: str,
    session_factory=AsyncSessionLocal,
) -> bool:
    coach = await get_coach_by_telegram_id(telegram_id)

    if coach is None:
        return False

    async with session_factory() as session:
        await session.execute(text("BEGIN IMMEDIATE"))

        try:
            result = await session.execute(
                select(AvailabilitySlot)
                .where(AvailabilitySlot.id == slot_id)
                .where(AvailabilitySlot.coach_id == coach.id)
                .where(AvailabilitySlot.status == "available")
            )
            slot = result.scalar_one_or_none()

            if slot is None:
                await session.rollback()
                return False

            slot.status = "cancelled"

            await safe_commit(session)
            return True

        except Exception:
            await session.rollback()
            raise


async def cancel_booked_slot_for_coach(
    *,
    telegram_id: int,
    slot_id: str,
    session_factory=AsyncSessionLocal,
) -> CancelBookedSlotResult:
    coach = await get_coach_by_telegram_id(telegram_id)

    if coach is None:
        return CancelBookedSlotResult(ok=False, reason="coach_not_found")

    async with session_factory() as session:
        await session.execute(text("BEGIN IMMEDIATE"))

        try:
            result = await session.execute(
                select(AvailabilitySlot, Appointment, Client, User)
                .join(Appointment, Appointment.slot_id == AvailabilitySlot.id)
                .join(Client, Appointment.client_id == Client.id)
                .join(User, Client.user_id == User.id)
                .where(AvailabilitySlot.id == slot_id)
                .where(AvailabilitySlot.coach_id == coach.id)
                .where(AvailabilitySlot.status == "booked")
                .where(Appointment.status == "booked")
            )

            row = result.one_or_none()

            if row is None:
                await session.rollback()
                return CancelBookedSlotResult(ok=False, reason="slot_not_found")

            slot, appointment, client, client_user = row

            slot.status = "cancelled"
            appointment.status = "cancelled_by_coach"

            starts_at = str(slot.starts_at)
            ends_at = str(slot.ends_at)
            client_telegram_id = client_user.telegram_id
            client_display_name = client.display_name

            await safe_commit(session)

            return CancelBookedSlotResult(
                ok=True,
                client_telegram_id=client_telegram_id,
                client_display_name=client_display_name,
                starts_at=starts_at,
                ends_at=ends_at,
            )

        except Exception:
            await session.rollback()
            raise
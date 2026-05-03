import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select, text

from app.db.database import AsyncSessionLocal, safe_commit
from app.db.models import (
    Appointment,
    AvailabilitySlot,
    Client,
    ClientCoachRelation,
    Coach,
    User,
)


@dataclass
class ClientContext:
    user: User
    client: Client
    coach: Coach


@dataclass
class BookSlotResult:
    ok: bool
    reason: str | None = None
    appointment_id: str | None = None
    slot_id: str | None = None
    starts_at: str | None = None
    ends_at: str | None = None


async def get_active_client_context(telegram_id: int) -> ClientContext | None:
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()

        if user is None or user.role != "client" or user.status != "active":
            return None

        client_result = await session.execute(
            select(Client).where(Client.user_id == user.id)
        )
        client = client_result.scalar_one_or_none()

        if client is None or client.status != "active":
            return None

        relation_result = await session.execute(
            select(ClientCoachRelation)
            .where(ClientCoachRelation.client_id == client.id)
            .where(ClientCoachRelation.status == "active")
        )
        relation = relation_result.scalar_one_or_none()

        if relation is None:
            return None

        coach_result = await session.execute(
            select(Coach).where(Coach.id == relation.coach_id)
        )
        coach = coach_result.scalar_one_or_none()

        if coach is None:
            return None

        return ClientContext(
            user=user,
            client=client,
            coach=coach,
        )


async def list_available_slots_for_client(
    telegram_id: int,
    limit: int = 10,
) -> list[AvailabilitySlot]:
    context = await get_active_client_context(telegram_id)

    if context is None:
        return []

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AvailabilitySlot)
            .where(AvailabilitySlot.coach_id == context.coach.id)
            .where(AvailabilitySlot.status == "available")
            .where(AvailabilitySlot.starts_at >= datetime.now(timezone.utc))
            .order_by(AvailabilitySlot.starts_at.asc())
            .limit(limit)
        )

        return list(result.scalars().all())


async def book_slot_for_client(
    *,
    telegram_id: int,
    slot_id: str,
) -> BookSlotResult:
    context = await get_active_client_context(telegram_id)

    if context is None:
        return BookSlotResult(ok=False, reason="client_not_found")

    async with AsyncSessionLocal() as session:
        await session.execute(text("BEGIN IMMEDIATE"))

        try:
            # 1. Атомарно занимаем слот.
            # Если слот уже занят, RETURNING не вернет строку.
            slot_result = await session.execute(
                text("""
                    UPDATE availability_slots
                    SET status = 'booked',
                        booked_by_client_id = :client_id,
                        booked_at = CURRENT_TIMESTAMP
                    WHERE id = :slot_id
                      AND coach_id = :coach_id
                      AND status = 'available'
                    RETURNING id, starts_at, ends_at
                """),
                {
                    "slot_id": slot_id,
                    "client_id": context.client.id,
                    "coach_id": context.coach.id,
                },
            )

            slot_row = slot_result.mappings().first()

            if slot_row is None:
                await session.rollback()
                return BookSlotResult(ok=False, reason="slot_not_available")

            appointment = Appointment(
                id=str(uuid.uuid4()),
                slot_id=slot_row["id"],
                coach_id=context.coach.id,
                client_id=context.client.id,
                status="booked",
            )

            session.add(appointment)

            await safe_commit(session)

            return BookSlotResult(
                ok=True,
                appointment_id=appointment.id,
                slot_id=slot_row["id"],
                starts_at=str(slot_row["starts_at"]),
                ends_at=str(slot_row["ends_at"]),
            )

        except Exception:
            await session.rollback()
            raise
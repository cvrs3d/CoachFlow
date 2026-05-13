from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import settings
from app.db.database import AsyncSessionLocal, safe_commit
from app.db.models import (
    Appointment,
    AvailabilitySlot,
    Client,
    ClientCoachRelation,
    Coach,
    User,
)
from app.utils.datetime import ensure_utc


@dataclass
class ClientBookingCard:
    appointment: Appointment
    slot: AvailabilitySlot
    client: Client
    coach: Coach
    coach_user: User
    can_cancel: bool
    cancellation_deadline_hours: int


@dataclass
class CancelClientBookingResult:
    ok: bool
    reason: str | None = None
    coach_telegram_id: int | None = None
    client_display_name: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


@dataclass
class ClientContext:
    user: User
    client: Client
    coach: Coach


async def get_active_client_context(
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> ClientContext | None:
    async with session_factory() as session:
        user_result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        user = user_result.scalar_one_or_none()

        if user is None or user.role != "client" or user.status != "active":
            return None

        client_result = await session.execute(select(Client).where(Client.user_id == user.id))
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

        coach_result = await session.execute(select(Coach).where(Coach.id == relation.coach_id))
        coach = coach_result.scalar_one_or_none()

        if coach is None:
            return None

        return ClientContext(
            user=user,
            client=client,
            coach=coach,
        )


async def list_future_bookings_for_client(
    *,
    telegram_id: int,
    limit: int = 10,
    session_factory=AsyncSessionLocal,
) -> list[tuple[Appointment, AvailabilitySlot]]:
    context = await get_active_client_context(telegram_id, session_factory=session_factory)

    if context is None:
        return []

    async with session_factory() as session:
        result = await session.execute(
            select(Appointment, AvailabilitySlot)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .where(Appointment.client_id == context.client.id)
            .where(Appointment.status == "booked")
            .where(AvailabilitySlot.starts_at >= datetime.now(UTC))
            .order_by(AvailabilitySlot.starts_at.asc())
            .limit(limit)
        )

        return [(appointment, slot) for appointment, slot in result.all()]


async def get_client_booking_card(
    *,
    telegram_id: int,
    appointment_id: str,
    session_factory=AsyncSessionLocal,
) -> ClientBookingCard | None:
    context = await get_active_client_context(telegram_id, session_factory=session_factory)

    if context is None:
        return None

    async with session_factory() as session:
        result = await session.execute(
            select(Appointment, AvailabilitySlot, Coach, User)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .join(Coach, Appointment.coach_id == Coach.id)
            .join(User, Coach.user_id == User.id)
            .where(Appointment.id == appointment_id)
            .where(Appointment.client_id == context.client.id)
            .where(Appointment.status == "booked")
        )

        row = result.one_or_none()

        if row is None:
            return None

        appointment, slot, coach, coach_user = row

        deadline = timedelta(hours=settings.client_cancellation_deadline_hours)
        can_cancel = ensure_utc(slot.starts_at) - datetime.now(UTC) > deadline

        return ClientBookingCard(
            appointment=appointment,
            slot=slot,
            client=context.client,
            coach=coach,
            coach_user=coach_user,
            can_cancel=can_cancel,
            cancellation_deadline_hours=settings.client_cancellation_deadline_hours,
        )


async def cancel_booking_by_client(
    *,
    telegram_id: int,
    appointment_id: str,
    session_factory=AsyncSessionLocal,
) -> CancelClientBookingResult:
    context = await get_active_client_context(telegram_id, session_factory=session_factory)

    if context is None:
        return CancelClientBookingResult(ok=False, reason="client_not_found")

    async with session_factory() as session:
        async with session.begin():
            try:
                result = await session.execute(
                    select(Appointment, AvailabilitySlot, Coach, User)
                    .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
                    .join(Coach, Appointment.coach_id == Coach.id)
                    .join(User, Coach.user_id == User.id)
                    .where(Appointment.id == appointment_id)
                    .where(Appointment.client_id == context.client.id)
                    .where(Appointment.status == "booked")
                    .where(AvailabilitySlot.status == "booked")
                )

                row = result.one_or_none()

                if row is None:
                    await session.rollback()
                    return CancelClientBookingResult(ok=False, reason="booking_not_found")

                appointment, slot, coach, coach_user = row

                slot_start_utc = ensure_utc(slot.starts_at)

                deadline = timedelta(hours=settings.client_cancellation_deadline_hours)

                if slot_start_utc - datetime.now(UTC) <= deadline:
                    await session.rollback()
                    return CancelClientBookingResult(ok=False, reason="too_late")

                appointment.status = "cancelled_by_client"

                # Клиент отменил заранее → слот снова доступен.
                slot.status = "available"
                slot.booked_by_client_id = None
                slot.booked_at = None

                starts_at = slot.starts_at
                ends_at = slot.ends_at
                coach_telegram_id = coach_user.telegram_id
                client_display_name = context.client.display_name

                await safe_commit(session)

                return CancelClientBookingResult(
                    ok=True,
                    coach_telegram_id=coach_telegram_id,
                    client_display_name=client_display_name,
                    starts_at=starts_at,
                    ends_at=ends_at,
                )

            except Exception:
                await session.rollback()
                raise

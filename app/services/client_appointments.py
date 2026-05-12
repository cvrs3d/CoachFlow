from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Appointment,
    AvailabilitySlot,
    Client,
    ClientCoachRelation,
    Coach,
    User,
)


@dataclass
class ClientAppointmentItem:
    appointment: Appointment
    slot: AvailabilitySlot


@dataclass
class ClientAppointmentsResult:
    ok: bool
    reason: str | None = None
    client: Client | None = None
    client_user: User | None = None
    coach_timezone: str | None = None
    future_items: list[ClientAppointmentItem] | None = None
    history_items: list[ClientAppointmentItem] | None = None


async def list_client_appointments_for_coach(
    *,
    coach_telegram_id: int,
    client_id: str,
    future_limit: int = 5,
    history_limit: int = 5,
    session_factory=AsyncSessionLocal,
) -> ClientAppointmentsResult:
    async with session_factory() as session:
        coach_result = await session.execute(
            select(Coach, User)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == coach_telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )
        coach_row = coach_result.one_or_none()

        if coach_row is None:
            return ClientAppointmentsResult(ok=False, reason="coach_not_found")

        coach, coach_user = coach_row

        client_result = await session.execute(
            select(Client, User, ClientCoachRelation)
            .join(User, Client.user_id == User.id)
            .join(ClientCoachRelation, ClientCoachRelation.client_id == Client.id)
            .where(Client.id == client_id)
            .where(ClientCoachRelation.coach_id == coach.id)
            .where(ClientCoachRelation.status == "active")
        )
        client_row = client_result.one_or_none()

        if client_row is None:
            return ClientAppointmentsResult(ok=False, reason="client_not_found")

        client, client_user, relation = client_row

        now = datetime.now(timezone.utc)

        future_result = await session.execute(
            select(Appointment, AvailabilitySlot)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .where(Appointment.coach_id == coach.id)
            .where(Appointment.client_id == client.id)
            .where(Appointment.status == "booked")
            .where(AvailabilitySlot.starts_at >= now)
            .order_by(AvailabilitySlot.starts_at.asc())
            .limit(future_limit)
        )

        history_result = await session.execute(
            select(Appointment, AvailabilitySlot)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .where(Appointment.coach_id == coach.id)
            .where(Appointment.client_id == client.id)
            .where(
                (Appointment.status != "booked")
                | (AvailabilitySlot.starts_at < now)
            )
            .order_by(AvailabilitySlot.starts_at.desc())
            .limit(history_limit)
        )

        future_items = [
            ClientAppointmentItem(appointment=appointment, slot=slot)
            for appointment, slot in future_result.all()
        ]

        history_items = [
            ClientAppointmentItem(appointment=appointment, slot=slot)
            for appointment, slot in history_result.all()
        ]

        return ClientAppointmentsResult(
            ok=True,
            client=client,
            client_user=client_user,
            coach_timezone=coach.timezone or "Europe/Prague",
            future_items=future_items,
            history_items=history_items,
        )
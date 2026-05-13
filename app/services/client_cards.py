from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Appointment,
    AvailabilitySlot,
    Client,
    ClientCoachRelation,
    Coach,
    MealReport,
    MealReview,
    User,
)


@dataclass
class ClientCardStats:
    reports_7d_count: int
    reviewed_7d_count: int
    needs_improvement_7d_count: int
    waiting_clarification_count: int


@dataclass
class ClientUpcomingAppointment:
    appointment_id: str
    slot_id: str
    starts_at: datetime
    ends_at: datetime
    status: str


@dataclass
class ClientCard:
    client: Client
    user: User
    relation: ClientCoachRelation
    upcoming_appointment: ClientUpcomingAppointment | None
    stats: ClientCardStats


@dataclass
class ClientCardResult:
    ok: bool
    reason: str | None = None
    card: ClientCard | None = None
    coach_timezone: str | None = None


async def get_client_card_for_coach(
    *,
    coach_telegram_id: int,
    client_id: str,
    session_factory=AsyncSessionLocal,
) -> ClientCardResult:
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
            return ClientCardResult(ok=False, reason="coach_not_found")

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
            return ClientCardResult(ok=False, reason="client_not_found")

        client, user, relation = client_row

        upcoming_appointment = await _get_upcoming_appointment_for_client(
            session=session,
            coach_id=coach.id,
            client_id=client.id,
        )

        stats = await _get_client_food_report_stats(
            session=session,
            coach_id=coach.id,
            client_id=client.id,
        )

        return ClientCardResult(
            ok=True,
            coach_timezone=coach.timezone or "Europe/Prague",
            card=ClientCard(
                client=client,
                user=user,
                relation=relation,
                upcoming_appointment=upcoming_appointment,
                stats=stats,
            ),
        )


async def _get_upcoming_appointment_for_client(
    *,
    session,
    coach_id: str,
    client_id: str,
) -> ClientUpcomingAppointment | None:
    now = datetime.now(UTC)

    result = await session.execute(
        select(Appointment, AvailabilitySlot)
        .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
        .where(Appointment.coach_id == coach_id)
        .where(Appointment.client_id == client_id)
        .where(Appointment.status == "booked")
        .where(AvailabilitySlot.starts_at >= now)
        .order_by(AvailabilitySlot.starts_at.asc())
        .limit(1)
    )
    row = result.one_or_none()

    if row is None:
        return None

    appointment, slot = row

    return ClientUpcomingAppointment(
        appointment_id=appointment.id,
        slot_id=slot.id,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
        status=appointment.status,
    )


async def _get_client_food_report_stats(
    *,
    session,
    coach_id: str,
    client_id: str,
) -> ClientCardStats:
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)

    reports_7d_count = await _scalar_count(
        session,
        select(func.count(MealReport.id))
        .where(MealReport.coach_id == coach_id)
        .where(MealReport.client_id == client_id)
        .where(MealReport.submitted_at >= seven_days_ago),
    )

    reviewed_7d_count = await _scalar_count(
        session,
        select(func.count(MealReport.id))
        .where(MealReport.coach_id == coach_id)
        .where(MealReport.client_id == client_id)
        .where(MealReport.status == "reviewed")
        .where(MealReport.reviewed_at >= seven_days_ago),
    )

    needs_improvement_7d_count = await _scalar_count(
        session,
        select(func.count(MealReview.id))
        .join(MealReport, MealReview.report_id == MealReport.id)
        .where(MealReview.coach_id == coach_id)
        .where(MealReport.client_id == client_id)
        .where(MealReview.verdict == "needs_improvement")
        .where(MealReview.created_at >= seven_days_ago),
    )

    waiting_clarification_count = await _scalar_count(
        session,
        select(func.count(MealReport.id))
        .where(MealReport.coach_id == coach_id)
        .where(MealReport.client_id == client_id)
        .where(MealReport.status == "needs_clarification"),
    )

    return ClientCardStats(
        reports_7d_count=reports_7d_count,
        reviewed_7d_count=reviewed_7d_count,
        needs_improvement_7d_count=needs_improvement_7d_count,
        waiting_clarification_count=waiting_clarification_count,
    )


async def _scalar_count(session, statement) -> int:
    result = await session.execute(statement)
    value = result.scalar_one()
    return int(value or 0)

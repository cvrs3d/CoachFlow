from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Appointment,
    AvailabilitySlot,
    ClientCoachRelation,
    Coach,
    MealReport,
    MealReview,
    User,
)


@dataclass
class CoachDashboardStats:
    today_appointments_count: int
    today_new_meal_reports_count: int
    pending_meal_reports_count: int
    waiting_clarification_count: int

    reports_7d_count: int
    reviewed_7d_count: int
    needs_improvement_7d_count: int
    active_clients_count: int


@dataclass
class CoachDashboardResult:
    ok: bool
    reason: str | None = None
    timezone_name: str | None = None
    stats: CoachDashboardStats | None = None


async def get_coach_dashboard(
    *,
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> CoachDashboardResult:
    async with session_factory() as session:
        coach_result = await session.execute(
            select(Coach, User)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )
        row = coach_result.one_or_none()

        if row is None:
            return CoachDashboardResult(ok=False, reason="coach_not_found")

        coach, user = row

        timezone_name = coach.timezone or "Europe/Prague"
        coach_tz = ZoneInfo(timezone_name)

        now_local = datetime.now(coach_tz)
        today_start_local = datetime.combine(
            now_local.date(),
            time.min,
            tzinfo=coach_tz,
        )
        tomorrow_start_local = today_start_local + timedelta(days=1)
        seven_days_ago_local = now_local - timedelta(days=7)

        today_start_utc = today_start_local.astimezone(ZoneInfo("UTC"))
        tomorrow_start_utc = tomorrow_start_local.astimezone(ZoneInfo("UTC"))
        seven_days_ago_utc = seven_days_ago_local.astimezone(ZoneInfo("UTC"))

        today_appointments_count = await _scalar_count(
            session,
            select(func.count(Appointment.id))
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .where(Appointment.coach_id == coach.id)
            .where(Appointment.status == "booked")
            .where(AvailabilitySlot.starts_at >= today_start_utc)
            .where(AvailabilitySlot.starts_at < tomorrow_start_utc),
        )

        today_new_meal_reports_count = await _scalar_count(
            session,
            select(func.count(MealReport.id))
            .where(MealReport.coach_id == coach.id)
            .where(MealReport.submitted_at >= today_start_utc)
            .where(MealReport.submitted_at < tomorrow_start_utc),
        )

        pending_meal_reports_count = await _scalar_count(
            session,
            select(func.count(MealReport.id))
            .where(MealReport.coach_id == coach.id)
            .where(MealReport.status.in_(["submitted", "in_review"])),
        )

        waiting_clarification_count = await _scalar_count(
            session,
            select(func.count(MealReport.id))
            .where(MealReport.coach_id == coach.id)
            .where(MealReport.status == "needs_clarification"),
        )

        reports_7d_count = await _scalar_count(
            session,
            select(func.count(MealReport.id))
            .where(MealReport.coach_id == coach.id)
            .where(MealReport.submitted_at >= seven_days_ago_utc),
        )

        reviewed_7d_count = await _scalar_count(
            session,
            select(func.count(MealReport.id))
            .where(MealReport.coach_id == coach.id)
            .where(MealReport.status == "reviewed")
            .where(MealReport.reviewed_at >= seven_days_ago_utc),
        )

        needs_improvement_7d_count = await _scalar_count(
            session,
            select(func.count(MealReview.id))
            .where(MealReview.coach_id == coach.id)
            .where(MealReview.verdict == "needs_improvement")
            .where(MealReview.created_at >= seven_days_ago_utc),
        )

        active_clients_count = await _scalar_count(
            session,
            select(func.count(ClientCoachRelation.id))
            .where(ClientCoachRelation.coach_id == coach.id)
            .where(ClientCoachRelation.status == "active"),
        )

        return CoachDashboardResult(
            ok=True,
            timezone_name=timezone_name,
            stats=CoachDashboardStats(
                today_appointments_count=today_appointments_count,
                today_new_meal_reports_count=today_new_meal_reports_count,
                pending_meal_reports_count=pending_meal_reports_count,
                waiting_clarification_count=waiting_clarification_count,
                reports_7d_count=reports_7d_count,
                reviewed_7d_count=reviewed_7d_count,
                needs_improvement_7d_count=needs_improvement_7d_count,
                active_clients_count=active_clients_count,
            ),
        )


async def _scalar_count(session, statement) -> int:
    result = await session.execute(statement)
    value = result.scalar_one()
    return int(value or 0)

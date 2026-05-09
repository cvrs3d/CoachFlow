import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Client,
    ClientCoachRelation,
    Coach,
    MealReport,
    MealReportPhoto,
    MealReview,
    User,
)

@dataclass
class ClientMealContext:
    user: User
    client: Client
    coach: Coach
    coach_user: User


@dataclass
class CreateMealReportResult:
    ok: bool
    reason: str | None = None
    report_id: str | None = None
    coach_telegram_id: int | None = None
    client_display_name: str | None = None
    meal_type: str | None = None
    submitted_at: datetime | None = None

@dataclass
class CoachMealContext:
    user: User
    coach: Coach


@dataclass
class MealReportCard:
    report: MealReport
    photo: MealReportPhoto
    client: Client
    client_user: User


@dataclass
class ReviewMealReportResult:
    ok: bool
    reason: str | None = None
    client_telegram_id: int | None = None
    client_display_name: str | None = None
    verdict: str | None = None
    report_status: str | None = None
    comment: str | None = None


async def get_active_client_meal_context(
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> ClientMealContext | None:
    async with session_factory() as session:
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

        coach_user_result = await session.execute(
            select(User).where(User.id == coach.user_id)
        )
        coach_user = coach_user_result.scalar_one_or_none()

        if coach_user is None or coach_user.status != "active":
            return None

        return ClientMealContext(
            user=user,
            client=client,
            coach=coach,
            coach_user=coach_user,
        )


async def create_meal_report_from_photo(
    *,
    telegram_id: int,
    meal_type: str,
    telegram_file_id: str,
    telegram_file_unique_id: str | None,
    client_comment: str | None = None,
    session_factory=AsyncSessionLocal,
) -> CreateMealReportResult:
    allowed_meal_types = {"breakfast", "lunch", "dinner", "snack", "other"}

    if meal_type not in allowed_meal_types:
        return CreateMealReportResult(ok=False, reason="invalid_meal_type")

    context = await get_active_client_meal_context(
        telegram_id,
        session_factory=session_factory,
    )

    if context is None:
        return CreateMealReportResult(ok=False, reason="client_not_found")

    submitted_at = datetime.now(timezone.utc)

    async with session_factory() as session:
        try:
            report = MealReport(
                id=str(uuid.uuid4()),
                checkin_id=None,
                client_id=context.client.id,
                coach_id=context.coach.id,
                meal_type=meal_type,
                status="submitted",
                client_comment=client_comment,
                submitted_at=submitted_at,
                reviewed_at=None,
            )
            session.add(report)
            await session.flush()

            photo = MealReportPhoto(
                id=str(uuid.uuid4()),
                report_id=report.id,
                stored_file_id=None,
                telegram_file_id=telegram_file_id,
                telegram_file_unique_id=telegram_file_unique_id,
                processing_status="stored",
            )
            session.add(photo)

            await session.commit()

            return CreateMealReportResult(
                ok=True,
                report_id=report.id,
                coach_telegram_id=context.coach_user.telegram_id,
                client_display_name=context.client.display_name,
                meal_type=meal_type,
                submitted_at=submitted_at,
            )

        except Exception:
            await session.rollback()
            raise

async def get_active_coach_meal_context(
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> CoachMealContext | None:
    async with session_factory() as session:
        result = await session.execute(
            select(Coach, User)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )

        row = result.one_or_none()

        if row is None:
            return None

        coach, user = row

        return CoachMealContext(
            user=user,
            coach=coach,
        )


async def list_pending_meal_reports_for_coach(
    *,
    telegram_id: int,
    limit: int = 10,
    session_factory=AsyncSessionLocal,
) -> list[tuple[MealReport, Client]]:
    context = await get_active_coach_meal_context(
        telegram_id,
        session_factory=session_factory,
    )

    if context is None:
        return []

    async with session_factory() as session:
        result = await session.execute(
            select(MealReport, Client)
            .join(Client, MealReport.client_id == Client.id)
            .where(MealReport.coach_id == context.coach.id)
            .where(MealReport.status.in_(["submitted", "in_review"]))
            .order_by(MealReport.submitted_at.asc())
            .limit(limit)
        )

        return list(result.all())


async def get_meal_report_for_coach(
    *,
    telegram_id: int,
    report_id: str,
    session_factory=AsyncSessionLocal,
) -> MealReportCard | None:
    context = await get_active_coach_meal_context(
        telegram_id,
        session_factory=session_factory,
    )

    if context is None:
        return None

    async with session_factory() as session:
        result = await session.execute(
            select(MealReport, MealReportPhoto, Client, User)
            .join(MealReportPhoto, MealReportPhoto.report_id == MealReport.id)
            .join(Client, MealReport.client_id == Client.id)
            .join(User, Client.user_id == User.id)
            .where(MealReport.id == report_id)
            .where(MealReport.coach_id == context.coach.id)
        )

        row = result.one_or_none()

        if row is None:
            return None

        report, photo, client, client_user = row

        return MealReportCard(
            report=report,
            photo=photo,
            client=client,
            client_user=client_user,
        )


async def review_meal_report(
    *,
    telegram_id: int,
    report_id: str,
    verdict: str,
    comment: str | None = None,
    session_factory=AsyncSessionLocal,
) -> ReviewMealReportResult:
    verdict_to_report_status = {
        "ok": "reviewed",
        "needs_improvement": "reviewed",
        "question": "needs_clarification",
    }

    if verdict not in verdict_to_report_status:
        return ReviewMealReportResult(ok=False, reason="invalid_verdict")

    context = await get_active_coach_meal_context(
        telegram_id,
        session_factory=session_factory,
    )

    if context is None:
        return ReviewMealReportResult(ok=False, reason="coach_not_found")

    async with session_factory() as session:
        try:
            result = await session.execute(
                select(MealReport, Client, User)
                .join(Client, MealReport.client_id == Client.id)
                .join(User, Client.user_id == User.id)
                .where(MealReport.id == report_id)
                .where(MealReport.coach_id == context.coach.id)
            )

            row = result.one_or_none()

            if row is None:
                return ReviewMealReportResult(ok=False, reason="report_not_found")

            report, client, client_user = row

            if report.status not in ("submitted", "in_review", "needs_clarification"):
                return ReviewMealReportResult(ok=False, reason="report_already_reviewed")

            existing_review_result = await session.execute(
                select(MealReview).where(MealReview.report_id == report.id)
            )
            existing_review = existing_review_result.scalar_one_or_none()

            if existing_review is not None:
                return ReviewMealReportResult(ok=False, reason="report_already_reviewed")

            review = MealReview(
                id=str(uuid.uuid4()),
                report_id=report.id,
                coach_id=context.coach.id,
                verdict=verdict,
                rating=None,
                comment=comment,
            )
            session.add(review)

            report.status = verdict_to_report_status[verdict]
            report.reviewed_at = datetime.now(timezone.utc)

            await session.commit()

            return ReviewMealReportResult(
                ok=True,
                client_telegram_id=client_user.telegram_id,
                client_display_name=client.display_name,
                verdict=verdict,
                comment=comment,
                report_status=report.status,
            )

        except Exception:
            await session.rollback()
            raise
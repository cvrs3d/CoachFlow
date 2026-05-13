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
class CoachClientMealReportItem:
    report: MealReport
    client: Client

@dataclass
class ClientMealReportCard:
    report: MealReport
    photo: MealReportPhoto
    review: MealReview | None = None

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
    latest_review: MealReview | None = None

@dataclass
class ReviewMealReportResult:
    ok: bool
    reason: str | None = None
    client_telegram_id: int | None = None
    client_display_name: str | None = None
    verdict: str | None = None
    report_status: str | None = None
    comment: str | None = None


@dataclass
class RespondToClarificationResult:
    ok: bool
    reason: str | None = None
    coach_telegram_id: int | None = None
    client_display_name: str | None = None
    report_id: str | None = None
    response_text: str | None = None

async def list_meal_reports_for_coach_client(
    *,
    coach_telegram_id: int,
    client_id: str,
    limit: int = 10,
    session_factory=AsyncSessionLocal,
) -> list[tuple[MealReport, Client]]:
    context = await get_active_coach_meal_context(
        coach_telegram_id,
        session_factory=session_factory,
    )

    if context is None:
        return []

    async with session_factory() as session:
        # Проверяем, что клиент действительно принадлежит этому тренеру.
        relation_result = await session.execute(
            select(ClientCoachRelation)
            .where(ClientCoachRelation.coach_id == context.coach.id)
            .where(ClientCoachRelation.client_id == client_id)
            .where(ClientCoachRelation.status == "active")
        )
        relation = relation_result.scalar_one_or_none()

        if relation is None:
            return []

        result = await session.execute(
            select(MealReport, Client)
            .join(Client, MealReport.client_id == Client.id)
            .where(MealReport.coach_id == context.coach.id)
            .where(MealReport.client_id == client_id)
            .order_by(MealReport.submitted_at.desc())
            .limit(limit)
        )

        return list(result.all())

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


async def list_meal_reports_for_coach_by_filter(
    *,
    telegram_id: int,
    report_filter: str,
    limit: int = 10,
    session_factory=AsyncSessionLocal,
) -> list[tuple[MealReport, Client]]:
    context = await get_active_coach_meal_context(
        telegram_id,
        session_factory=session_factory,
    )

    if context is None:
        return []

    filter_statuses = {
        "pending": ["submitted", "in_review"],
        "clarification": ["needs_clarification"],
        "reviewed": ["reviewed"],
    }

    statuses = filter_statuses.get(report_filter)

    if statuses is None:
        return []

    async with session_factory() as session:
        result = await session.execute(
            select(MealReport, Client)
            .join(Client, MealReport.client_id == Client.id)
            .where(MealReport.coach_id == context.coach.id)
            .where(MealReport.status.in_(statuses))
            .order_by(MealReport.submitted_at.desc())
            .limit(limit)
        )

        return list(result.all())

async def list_pending_meal_reports_for_coach(
    *,
    telegram_id: int,
    limit: int = 10,
    session_factory=AsyncSessionLocal,
) -> list[tuple[MealReport, Client]]:
    return await list_meal_reports_for_coach_by_filter(
        telegram_id=telegram_id,
        report_filter="pending",
        limit=limit,
        session_factory=session_factory,
    )


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

        latest_review_result = await session.execute(
            select(MealReview)
            .where(MealReview.report_id == report.id)
            .order_by(MealReview.created_at.desc())
            .limit(1)
        )
        latest_review = latest_review_result.scalar_one_or_none()

    return MealReportCard(
        report=report,
        photo=photo,
        client=client,
        client_user=client_user,
        latest_review=latest_review,
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
        "bad": "reviewed",
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
                report_status=report.status,
                comment=comment,
            )

        except Exception:
            await session.rollback()
            raise


async def list_meal_reports_for_client_by_filter(
    *,
    telegram_id: int,
    report_filter: str,
    limit: int = 10,
    session_factory=AsyncSessionLocal,
) -> list[MealReport]:
    context = await get_active_client_meal_context(
        telegram_id,
        session_factory=session_factory,
    )

    if context is None:
        return []

    filter_statuses = {
        "all": None,
        "pending": ["submitted", "in_review"],
        "reviewed": ["reviewed"],
        "clarification": ["needs_clarification"],
    }

    statuses = filter_statuses.get(report_filter)

    if report_filter not in filter_statuses:
        return []

    async with session_factory() as session:
        statement = (
            select(MealReport)
            .where(MealReport.client_id == context.client.id)
            .order_by(MealReport.submitted_at.desc())
            .limit(limit)
        )

        if statuses is not None:
            statement = statement.where(MealReport.status.in_(statuses))

        result = await session.execute(statement)

        return list(result.scalars().all())
    
async def list_meal_reports_for_client(
    *,
    telegram_id: int,
    limit: int = 10,
    session_factory=AsyncSessionLocal,
) -> list[MealReport]:
    return await list_meal_reports_for_client_by_filter(
        telegram_id=telegram_id,
        report_filter="all",
        limit=limit,
        session_factory=session_factory,
    )

async def get_meal_report_for_client(
    *,
    telegram_id: int,
    report_id: str,
    session_factory=AsyncSessionLocal,
) -> ClientMealReportCard | None:
    context = await get_active_client_meal_context(
        telegram_id,
        session_factory=session_factory,
    )

    if context is None:
        return None

    async with session_factory() as session:
        result = await session.execute(
            select(MealReport, MealReportPhoto)
            .join(MealReportPhoto, MealReportPhoto.report_id == MealReport.id)
            .where(MealReport.id == report_id)
            .where(MealReport.client_id == context.client.id)
        )

        row = result.one_or_none()

        if row is None:
            return None

        report, photo = row

        review_result = await session.execute(
            select(MealReview)
            .where(MealReview.report_id == report.id)
            .order_by(MealReview.created_at.desc())
            .limit(1)
        )
        review = review_result.scalar_one_or_none()

        return ClientMealReportCard(
            report=report,
            photo=photo,
            review=review,
        )

async def respond_to_meal_report_clarification(
    *,
    telegram_id: int,
    report_id: str,
    response_text: str,
    session_factory=AsyncSessionLocal,
) -> RespondToClarificationResult:
    response_text = response_text.strip()

    if len(response_text) < 2:
        return RespondToClarificationResult(ok=False, reason="response_too_short")

    if len(response_text) > 1000:
        return RespondToClarificationResult(ok=False, reason="response_too_long")

    context = await get_active_client_meal_context(
        telegram_id,
        session_factory=session_factory,
    )

    if context is None:
        return RespondToClarificationResult(ok=False, reason="client_not_found")

    async with session_factory() as session:
        try:
            result = await session.execute(
                select(MealReport)
                .where(MealReport.id == report_id)
                .where(MealReport.client_id == context.client.id)
            )
            report = result.scalar_one_or_none()

            if report is None:
                return RespondToClarificationResult(ok=False, reason="report_not_found")

            if report.status != "needs_clarification":
                return RespondToClarificationResult(ok=False, reason="report_not_waiting_for_clarification")

            report.clarification_response = response_text
            report.clarification_responded_at = datetime.now(timezone.utc)

            # Возвращаем отчет обратно в очередь тренеру.
            report.status = "submitted"

            await session.commit()

            return RespondToClarificationResult(
                ok=True,
                coach_telegram_id=context.coach_user.telegram_id,
                client_display_name=context.client.display_name,
                report_id=report.id,
                response_text=response_text,
            )

        except Exception:
            await session.rollback()
            raise
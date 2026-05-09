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
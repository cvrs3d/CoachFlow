import uuid
from dataclasses import dataclass

from sqlalchemy import select

from app.db.database import AsyncSessionLocal

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import (
    Appointment,
    AvailabilitySlot,
    Client,
    DataDeletionRequest,
    MealCheckin,
    MealReport,
    MealReportPhoto,
    MealReview,
    User,
)

@dataclass
class RequestDataDeletionResult:
    ok: bool
    reason: str | None = None
    request_id: str | None = None

@dataclass
class ExportUserDataResult:
    ok: bool
    reason: str | None = None
    filename: str | None = None
    file_bytes: bytes | None = None

@dataclass
class RetentionCleanupResult:
    archived_photos_count: int = 0


async def archive_old_meal_report_photo_references(
    *,
    older_than_days: int = 180,
    session_factory=AsyncSessionLocal,
) -> RetentionCleanupResult:
    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)

    async with session_factory() as session:
        result = await session.execute(
            select(MealReportPhoto)
            .where(MealReportPhoto.created_at < cutoff)
            .where(MealReportPhoto.processing_status != "archived")
        )
        photos = list(result.scalars().all())

        for photo in photos:
            photo.telegram_file_id = None
            photo.telegram_file_unique_id = None
            photo.processing_status = "archived"

        await session.commit()

        return RetentionCleanupResult(archived_photos_count=len(photos))

def _dt(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


async def export_user_data(
    *,
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> ExportUserDataResult:
    async with session_factory() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            return ExportUserDataResult(ok=False, reason="user_not_found")

        data = {
            "user": {
                "id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "role": user.role,
                "status": user.status,
                "created_at": _dt(user.created_at),
            },
            "client": None,
            "appointments": [],
            "meal_checkins": [],
            "meal_reports": [],
        }

        client_result = await session.execute(
            select(Client).where(Client.user_id == user.id)
        )
        client = client_result.scalar_one_or_none()

        if client is None:
            payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            return ExportUserDataResult(
                ok=True,
                filename="coachflow_data_export.json",
                file_bytes=payload,
            )

        data["client"] = {
            "id": client.id,
            "display_name": client.display_name,
            "goal": client.goal,
            "status": client.status,
            "created_at": _dt(client.created_at),
        }

        appointments_result = await session.execute(
            select(Appointment, AvailabilitySlot)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .where(Appointment.client_id == client.id)
            .order_by(AvailabilitySlot.starts_at.desc())
        )

        for appointment, slot in appointments_result.all():
            data["appointments"].append(
                {
                    "id": appointment.id,
                    "status": appointment.status,
                    "starts_at": _dt(slot.starts_at),
                    "ends_at": _dt(slot.ends_at),
                    "cancelled_at": _dt(appointment.cancelled_at),
                    "cancel_reason": appointment.cancel_reason,
                }
            )

        checkins_result = await session.execute(
            select(MealCheckin)
            .where(MealCheckin.client_id == client.id)
            .order_by(MealCheckin.scheduled_at.desc())
        )

        for checkin in checkins_result.scalars().all():
            data["meal_checkins"].append(
                {
                    "id": checkin.id,
                    "meal_type": checkin.meal_type,
                    "scheduled_at": _dt(checkin.scheduled_at),
                    "status": checkin.status,
                }
            )

        reports_result = await session.execute(
            select(MealReport)
            .where(MealReport.client_id == client.id)
            .order_by(MealReport.submitted_at.desc())
        )
        reports = list(reports_result.scalars().all())

        for report in reports:
            photos_result = await session.execute(
                select(MealReportPhoto).where(MealReportPhoto.report_id == report.id)
            )
            photos = photos_result.scalars().all()

            reviews_result = await session.execute(
                select(MealReview)
                .where(MealReview.report_id == report.id)
                .order_by(MealReview.created_at.asc())
            )
            reviews = reviews_result.scalars().all()

            data["meal_reports"].append(
                {
                    "id": report.id,
                    "checkin_id": report.checkin_id,
                    "meal_type": report.meal_type,
                    "status": report.status,
                    "client_comment": report.client_comment,
                    "submitted_at": _dt(report.submitted_at),
                    "reviewed_at": _dt(report.reviewed_at),
                    "clarification_response": report.clarification_response,
                    "clarification_responded_at": _dt(report.clarification_responded_at),
                    "photos": [
                        {
                            "telegram_file_id": photo.telegram_file_id,
                            "telegram_file_unique_id": photo.telegram_file_unique_id,
                            "processing_status": photo.processing_status,
                            "created_at": _dt(photo.created_at),
                        }
                        for photo in photos
                    ],
                    "reviews": [
                        {
                            "verdict": review.verdict,
                            "rating": review.rating,
                            "comment": review.comment,
                            "created_at": _dt(review.created_at),
                        }
                        for review in reviews
                    ],
                }
            )

        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

        return ExportUserDataResult(
            ok=True,
            filename="coachflow_data_export.json",
            file_bytes=payload,
        )



async def request_data_deletion(
    *,
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> RequestDataDeletionResult:
    async with session_factory() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            return RequestDataDeletionResult(ok=False, reason="user_not_found")

        existing_result = await session.execute(
            select(DataDeletionRequest)
            .where(DataDeletionRequest.user_id == user.id)
            .where(DataDeletionRequest.status == "pending")
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            return RequestDataDeletionResult(
                ok=True,
                reason="already_pending",
                request_id=existing.id,
            )

        request = DataDeletionRequest(
            id=str(uuid.uuid4()),
            user_id=user.id,
            telegram_id=telegram_id,
            status="pending",
        )

        session.add(request)
        await session.commit()

        return RequestDataDeletionResult(ok=True, request_id=request.id)
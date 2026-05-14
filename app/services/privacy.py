import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Appointment,
    AvailabilitySlot,
    Client,
    ClientCoachRelation,
    DataDeletionRequest,
    MealCheckin,
    MealReport,
    MealReportPhoto,
    MealReview,
    User,
)

@dataclass
class ProcessDataDeletionRequestResult:
    ok: bool
    reason: str | None = None
    request_id: str | None = None
    anonymized_photos_count: int = 0
    cancelled_appointments_count: int = 0

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

async def process_data_deletion_request(
    *,
    request_id: str,
    admin_note: str | None = None,
    session_factory=AsyncSessionLocal,
) -> ProcessDataDeletionRequestResult:
    now = datetime.now(timezone.utc)

    async with session_factory() as session:
        request_result = await session.execute(
            select(DataDeletionRequest)
            .where(DataDeletionRequest.id == request_id)
        )
        deletion_request = request_result.scalar_one_or_none()

        if deletion_request is None:
            return ProcessDataDeletionRequestResult(
                ok=False,
                reason="request_not_found",
                request_id=request_id,
            )

        if deletion_request.status != "pending":
            return ProcessDataDeletionRequestResult(
                ok=False,
                reason="request_not_pending",
                request_id=request_id,
            )

        user_result = await session.execute(
            select(User).where(User.id == deletion_request.user_id)
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            deletion_request.status = "rejected"
            deletion_request.processed_at = now
            deletion_request.admin_note = admin_note or "User not found."
            await session.commit()

            return ProcessDataDeletionRequestResult(
                ok=False,
                reason="user_not_found",
                request_id=request_id,
            )

        anonymized_photos_count = 0
        cancelled_appointments_count = 0

        client_result = await session.execute(
            select(Client).where(Client.user_id == user.id)
        )
        client = client_result.scalar_one_or_none()

        if client is not None:
            # 1. Deactivate client profile and remove direct PII.
            client.display_name = "Deleted user"
            client.goal = None
            client.status = "inactive"

            # 2. Deactivate coach relations.
            relations_result = await session.execute(
                select(ClientCoachRelation)
                .where(ClientCoachRelation.client_id == client.id)
                .where(ClientCoachRelation.status == "active")
            )
            relations = list(relations_result.scalars().all())

            for relation in relations:
                relation.status = "inactive"

            # 3. Cancel future booked appointments and release slots.
            appointments_result = await session.execute(
                select(Appointment, AvailabilitySlot)
                .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
                .where(Appointment.client_id == client.id)
                .where(Appointment.status == "booked")
                .where(AvailabilitySlot.starts_at >= now)
            )
            appointment_rows = list(appointments_result.all())

            for appointment, slot in appointment_rows:
                appointment.status = "cancelled_by_client"
                appointment.cancelled_at = now
                appointment.cancel_reason = "data_deletion_request"

                slot.status = "available"
                slot.booked_by_client_id = None
                slot.booked_at = None

                cancelled_appointments_count += 1

            # 4. Cancel pending/sent meal checkins.
            checkins_result = await session.execute(
                select(MealCheckin)
                .where(MealCheckin.client_id == client.id)
                .where(MealCheckin.status.in_(["pending", "sent"]))
            )
            checkins = list(checkins_result.scalars().all())

            for checkin in checkins:
                checkin.status = "cancelled"

            # 5. Remove Telegram photo identifiers from meal reports.
            photos_result = await session.execute(
                select(MealReportPhoto)
                .join(MealReport, MealReportPhoto.report_id == MealReport.id)
                .where(MealReport.client_id == client.id)
                .where(MealReportPhoto.processing_status != "archived")
            )
            photos = list(photos_result.scalars().all())

            for photo in photos:
                photo.telegram_file_id = None
                photo.telegram_file_unique_id = None
                photo.processing_status = "archived"
                anonymized_photos_count += 1

        # 6. Remove direct Telegram username. Keep telegram_id only for audit/abuse prevention.
        # If later you want stronger deletion, you need a separate anonymized mapping strategy.
        user.username = None
        user.status = "blocked"

        deletion_request.status = "processed"
        deletion_request.processed_at = now
        deletion_request.admin_note = admin_note

        await session.commit()

        return ProcessDataDeletionRequestResult(
            ok=True,
            request_id=request_id,
            anonymized_photos_count=anonymized_photos_count,
            cancelled_appointments_count=cancelled_appointments_count,
        )

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
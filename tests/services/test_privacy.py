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
    User,
)
from app.services.privacy import (
    archive_old_meal_report_photo_references,
    process_data_deletion_request,
    request_data_deletion,
)
from tests.factories.entities import create_client_for_coach, create_coach


async def test_archive_old_meal_report_photo_references(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Client",
        )

        report = MealReport(
            id="report-old",
            checkin_id=None,
            client_id=client.id,
            coach_id=coach.id,
            meal_type="lunch",
            status="submitted",
            client_comment=None,
            submitted_at=datetime.now(timezone.utc) - timedelta(days=200),
            reviewed_at=None,
            clarification_response=None,
            clarification_responded_at=None,
        )
        session.add(report)
        await session.flush()

        photo = MealReportPhoto(
            id="photo-old",
            report_id=report.id,
            stored_file_id=None,
            telegram_file_id="file-id",
            telegram_file_unique_id="unique-id",
            processing_status="stored",
            created_at=datetime.now(timezone.utc) - timedelta(days=200),
        )
        session.add(photo)

        await session.commit()

    result = await archive_old_meal_report_photo_references(
        older_than_days=180,
        session_factory=session_factory,
    )

    assert result.archived_photos_count == 1

    async with session_factory() as session:
        photo_result = await session.execute(
            select(MealReportPhoto).where(MealReportPhoto.id == "photo-old")
        )
        photo = photo_result.scalar_one()

        assert photo.telegram_file_id is None
        assert photo.telegram_file_unique_id is None
        assert photo.processing_status == "archived"

async def test_process_data_deletion_request_anonymizes_client_data(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Client Name",
        )

        client.goal = "Lose weight"

        report = MealReport(
            id="report-1",
            checkin_id=None,
            client_id=client.id,
            coach_id=coach.id,
            meal_type="lunch",
            status="submitted",
            client_comment="my comment",
            submitted_at=datetime.now(timezone.utc),
            reviewed_at=None,
            clarification_response=None,
            clarification_responded_at=None,
        )
        session.add(report)
        await session.flush()

        photo = MealReportPhoto(
            id="photo-1",
            report_id=report.id,
            stored_file_id=None,
            telegram_file_id="file-id",
            telegram_file_unique_id="unique-id",
            processing_status="stored",
        )
        session.add(photo)

        await session.commit()

    request_result = await request_data_deletion(
        telegram_id=2001,
        session_factory=session_factory,
    )

    assert request_result.ok is True
    assert request_result.request_id is not None

    process_result = await process_data_deletion_request(
        request_id=request_result.request_id,
        admin_note="test",
        session_factory=session_factory,
    )

    assert process_result.ok is True
    assert process_result.anonymized_photos_count == 1

    async with session_factory() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == 2001)
        )
        user = user_result.scalar_one()

        client_result = await session.execute(
            select(Client).where(Client.user_id == user.id)
        )
        client = client_result.scalar_one()

        photo_result = await session.execute(
            select(MealReportPhoto).where(MealReportPhoto.id == "photo-1")
        )
        photo = photo_result.scalar_one()

        request_db_result = await session.execute(
            select(DataDeletionRequest).where(DataDeletionRequest.id == request_result.request_id)
        )
        deletion_request = request_db_result.scalar_one()

        assert user.username is None
        assert user.status == "blocked"

        assert client.display_name == "Deleted user"
        assert client.goal is None
        assert client.status == "inactive"

        assert photo.telegram_file_id is None
        assert photo.telegram_file_unique_id is None
        assert photo.processing_status == "archived"

        assert deletion_request.status == "processed"
        assert deletion_request.processed_at is not None
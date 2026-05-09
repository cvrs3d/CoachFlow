from sqlalchemy import select

from app.db.models import MealReport, MealReportPhoto
from app.services.meal_reports import (
    create_meal_report_from_photo,
    get_active_client_meal_context,
)
from tests.factories.entities import (
    create_client_for_coach,
    create_coach,
    create_user,
)


async def test_get_active_client_meal_context(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    context = await get_active_client_meal_context(
        2001,
        session_factory=session_factory,
    )

    assert context is not None
    assert context.user.telegram_id == 2001
    assert context.client.display_name == "Test Client"
    assert context.coach.id == coach.id
    assert context.coach_user.telegram_id == 1001


async def test_client_can_create_meal_report_with_photo(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

        client_id = client.id
        coach_id = coach.id

    result = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        client_comment="Рис и курица",
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.reason is None
    assert result.report_id is not None
    assert result.coach_telegram_id == 1001
    assert result.client_display_name == "Test Client"
    assert result.meal_type == "lunch"

    async with session_factory() as session:
        report_result = await session.execute(
            select(MealReport).where(MealReport.id == result.report_id)
        )
        report = report_result.scalar_one()

        assert report.client_id == client_id
        assert report.coach_id == coach_id
        assert report.meal_type == "lunch"
        assert report.status == "submitted"
        assert report.client_comment == "Рис и курица"

        photo_result = await session.execute(
            select(MealReportPhoto).where(MealReportPhoto.report_id == report.id)
        )
        photo = photo_result.scalar_one()

        assert photo.telegram_file_id == "telegram-file-id-123"
        assert photo.telegram_file_unique_id == "telegram-unique-id-123"
        assert photo.processing_status == "stored"
        assert photo.stored_file_id is None


async def test_inactive_client_cannot_create_meal_report(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Inactive Client",
        )

        client.status = "inactive"

        await session.commit()

    result = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    assert result.ok is False
    assert result.reason == "client_not_found"

    async with session_factory() as session:
        reports_result = await session.execute(select(MealReport))
        reports = reports_result.scalars().all()

        assert reports == []


async def test_invalid_meal_type_is_rejected(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
        )
        await session.commit()

    result = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="pizza",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    assert result.ok is False
    assert result.reason == "invalid_meal_type"

    async with session_factory() as session:
        reports_result = await session.execute(select(MealReport))
        reports = reports_result.scalars().all()

        assert reports == []
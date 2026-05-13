from sqlalchemy import select

from app.db.models import MealReview, MealReportPhoto, MealReport
from app.services.meal_reports import (
    create_meal_report_from_photo,
    get_active_client_meal_context,
    get_meal_report_for_client,
    get_meal_report_for_coach,
    list_meal_reports_for_client,
    list_pending_meal_reports_for_coach,
    review_meal_report,
)
from tests.factories.entities import (
    create_client_for_coach,
    create_coach,
    create_user,
)
from app.services.meal_reports import list_meal_reports_for_coach_by_filter
from app.services.meal_reports import respond_to_meal_report_clarification
from app.services.meal_reports import list_meal_reports_for_coach_client
from app.services.meal_reports import list_meal_reports_for_client_by_filter

async def test_client_can_filter_pending_meal_reports(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-1",
        telegram_file_unique_id="telegram-unique-id-1",
        session_factory=session_factory,
    )

    reports = await list_meal_reports_for_client_by_filter(
        telegram_id=2001,
        report_filter="pending",
        session_factory=session_factory,
    )

    assert len(reports) == 1
    assert reports[0].id == created.report_id
    assert reports[0].status == "submitted"


async def test_client_can_filter_reviewed_meal_reports(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-1",
        telegram_file_unique_id="telegram-unique-id-1",
        session_factory=session_factory,
    )

    reviewed = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="ok",
        session_factory=session_factory,
    )

    assert reviewed.ok is True

    pending_reports = await list_meal_reports_for_client_by_filter(
        telegram_id=2001,
        report_filter="pending",
        session_factory=session_factory,
    )

    reviewed_reports = await list_meal_reports_for_client_by_filter(
        telegram_id=2001,
        report_filter="reviewed",
        session_factory=session_factory,
    )

    assert pending_reports == []
    assert len(reviewed_reports) == 1
    assert reviewed_reports[0].id == created.report_id
    assert reviewed_reports[0].status == "reviewed"

async def test_client_can_filter_clarification_meal_reports(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="dinner",
        telegram_file_id="telegram-file-id-1",
        telegram_file_unique_id="telegram-unique-id-1",
        session_factory=session_factory,
    )

    reviewed = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="question",
        comment="Что было в соусе?",
        session_factory=session_factory,
    )

    assert reviewed.ok is True

    clarification_reports = await list_meal_reports_for_client_by_filter(
        telegram_id=2001,
        report_filter="clarification",
        session_factory=session_factory,
    )

    pending_reports = await list_meal_reports_for_client_by_filter(
        telegram_id=2001,
        report_filter="pending",
        session_factory=session_factory,
    )

    assert len(clarification_reports) == 1
    assert clarification_reports[0].id == created.report_id
    assert clarification_reports[0].status == "needs_clarification"
    assert pending_reports == []

async def test_client_filter_does_not_show_other_client_reports(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)

        client_user_1, client_1, relation_1 = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Client One",
        )

        client_user_2, client_2, relation_2 = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2002,
            display_name="Client Two",
        )

        await session.commit()

    report_1 = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-1",
        telegram_file_unique_id="telegram-unique-id-1",
        session_factory=session_factory,
    )

    report_2 = await create_meal_report_from_photo(
        telegram_id=2002,
        meal_type="dinner",
        telegram_file_id="telegram-file-id-2",
        telegram_file_unique_id="telegram-unique-id-2",
        session_factory=session_factory,
    )

    client_1_reports = await list_meal_reports_for_client_by_filter(
        telegram_id=2001,
        report_filter="all",
        session_factory=session_factory,
    )

    client_2_reports = await list_meal_reports_for_client_by_filter(
        telegram_id=2002,
        report_filter="all",
        session_factory=session_factory,
    )

    assert len(client_1_reports) == 1
    assert client_1_reports[0].id == report_1.report_id

    assert len(client_2_reports) == 1
    assert client_2_reports[0].id == report_2.report_id

async def test_client_invalid_meal_report_filter_returns_empty_list(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-1",
        telegram_file_unique_id="telegram-unique-id-1",
        session_factory=session_factory,
    )

    reports = await list_meal_reports_for_client_by_filter(
        telegram_id=2001,
        report_filter="unknown",
        session_factory=session_factory,
    )

    assert reports == []

async def test_client_cannot_list_meal_reports_for_coach_client_filter(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Client One",
        )

        await session.commit()

        client_id = client.id

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-1",
        telegram_file_unique_id="telegram-unique-id-1",
        session_factory=session_factory,
    )

    assert created.ok is True

    reports = await list_meal_reports_for_coach_client(
        coach_telegram_id=2001,
        client_id=client_id,
        session_factory=session_factory,
    )

    assert reports == []

async def test_coach_cannot_list_meal_reports_for_other_coach_client(session_factory):
    async with session_factory() as session:
        coach_user_1, coach_1 = await create_coach(session, telegram_id=1001)
        client_user_1, client_1, relation_1 = await create_client_for_coach(
            session,
            coach=coach_1,
            telegram_id=2001,
            display_name="Client One",
        )

        coach_user_2, coach_2 = await create_coach(session, telegram_id=1002)
        client_user_2, client_2, relation_2 = await create_client_for_coach(
            session,
            coach=coach_2,
            telegram_id=2002,
            display_name="Client Two",
        )

        await session.commit()

        client_2_id = client_2.id

    report_2 = await create_meal_report_from_photo(
        telegram_id=2002,
        meal_type="dinner",
        telegram_file_id="telegram-file-id-2",
        telegram_file_unique_id="telegram-unique-id-2",
        session_factory=session_factory,
    )

    assert report_2.ok is True

    reports = await list_meal_reports_for_coach_client(
        coach_telegram_id=1001,
        client_id=client_2_id,
        session_factory=session_factory,
    )

    assert reports == []

async def test_coach_can_list_meal_reports_for_specific_client(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)

        client_user_1, client_1, relation_1 = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Client One",
        )

        client_user_2, client_2, relation_2 = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2002,
            display_name="Client Two",
        )

        await session.commit()

        client_1_id = client_1.id
        client_2_id = client_2.id

    report_1 = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-1",
        telegram_file_unique_id="telegram-unique-id-1",
        session_factory=session_factory,
    )

    report_2 = await create_meal_report_from_photo(
        telegram_id=2002,
        meal_type="dinner",
        telegram_file_id="telegram-file-id-2",
        telegram_file_unique_id="telegram-unique-id-2",
        session_factory=session_factory,
    )

    assert report_1.ok is True
    assert report_2.ok is True

    client_1_reports = await list_meal_reports_for_coach_client(
        coach_telegram_id=1001,
        client_id=client_1_id,
        session_factory=session_factory,
    )

    client_2_reports = await list_meal_reports_for_coach_client(
        coach_telegram_id=1001,
        client_id=client_2_id,
        session_factory=session_factory,
    )

    assert len(client_1_reports) == 1
    assert client_1_reports[0][0].id == report_1.report_id
    assert client_1_reports[0][1].display_name == "Client One"

    assert len(client_2_reports) == 1
    assert client_2_reports[0][0].id == report_2.report_id
    assert client_2_reports[0][1].display_name == "Client Two"

async def test_coach_filter_does_not_show_other_coach_reports(session_factory):
    async with session_factory() as session:
        coach_user_1, coach_1 = await create_coach(session, telegram_id=1001)
        client_user_1, client_1, relation_1 = await create_client_for_coach(
            session,
            coach=coach_1,
            telegram_id=2001,
            display_name="Client One",
        )

        coach_user_2, coach_2 = await create_coach(session, telegram_id=1002)
        client_user_2, client_2, relation_2 = await create_client_for_coach(
            session,
            coach=coach_2,
            telegram_id=2002,
            display_name="Client Two",
        )

        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    coach_1_reports = await list_meal_reports_for_coach_by_filter(
        telegram_id=1001,
        report_filter="pending",
        session_factory=session_factory,
    )

    coach_2_reports = await list_meal_reports_for_coach_by_filter(
        telegram_id=1002,
        report_filter="pending",
        session_factory=session_factory,
    )

    assert len(coach_1_reports) == 1
    assert coach_1_reports[0][0].id == created.report_id
    assert coach_2_reports == []

async def test_coach_can_filter_clarification_meal_reports(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    reviewed = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="question",
        comment="Что было в соусе?",
        session_factory=session_factory,
    )

    assert reviewed.ok is True

    clarification = await list_meal_reports_for_coach_by_filter(
        telegram_id=1001,
        report_filter="clarification",
        session_factory=session_factory,
    )

    pending = await list_meal_reports_for_coach_by_filter(
        telegram_id=1001,
        report_filter="pending",
        session_factory=session_factory,
    )

    assert len(clarification) == 1
    assert clarification[0][0].status == "needs_clarification"
    assert pending == []

async def test_coach_can_filter_reviewed_meal_reports(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    reviewed = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="ok",
        session_factory=session_factory,
    )

    assert reviewed.ok is True

    pending = await list_meal_reports_for_coach_by_filter(
        telegram_id=1001,
        report_filter="pending",
        session_factory=session_factory,
    )

    reviewed_reports = await list_meal_reports_for_coach_by_filter(
        telegram_id=1001,
        report_filter="reviewed",
        session_factory=session_factory,
    )

    assert pending == []
    assert len(reviewed_reports) == 1
    assert reviewed_reports[0][0].id == created.report_id
    assert reviewed_reports[0][0].status == "reviewed"


async def test_coach_can_filter_pending_meal_reports(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    reports = await list_meal_reports_for_coach_by_filter(
        telegram_id=1001,
        report_filter="pending",
        session_factory=session_factory,
    )

    assert len(reports) == 1
    assert reports[0][0].id == created.report_id
    assert reports[0][0].status == "submitted"

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

async def test_coach_can_list_own_pending_meal_reports(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    assert created.ok is True

    reports = await list_pending_meal_reports_for_coach(
        telegram_id=1001,
        session_factory=session_factory,
    )

    assert len(reports) == 1

    report, listed_client = reports[0]

    assert report.id == created.report_id
    assert report.status == "submitted"
    assert listed_client.display_name == "Test Client"


async def test_coach_cannot_list_other_coach_reports(session_factory):
    async with session_factory() as session:
        coach_user_1, coach_1 = await create_coach(session, telegram_id=1001)
        client_user_1, client_1, relation_1 = await create_client_for_coach(
            session,
            coach=coach_1,
            telegram_id=2001,
            display_name="Client One",
        )

        coach_user_2, coach_2 = await create_coach(session, telegram_id=1002)
        client_user_2, client_2, relation_2 = await create_client_for_coach(
            session,
            coach=coach_2,
            telegram_id=2002,
            display_name="Client Two",
        )

        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    assert created.ok is True

    coach_1_reports = await list_pending_meal_reports_for_coach(
        telegram_id=1001,
        session_factory=session_factory,
    )
    coach_2_reports = await list_pending_meal_reports_for_coach(
        telegram_id=1002,
        session_factory=session_factory,
    )

    assert len(coach_1_reports) == 1
    assert len(coach_2_reports) == 0


async def test_coach_can_open_own_meal_report(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="dinner",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        client_comment="Курица и овощи",
        session_factory=session_factory,
    )

    assert created.ok is True

    card = await get_meal_report_for_coach(
        telegram_id=1001,
        report_id=created.report_id,
        session_factory=session_factory,
    )

    assert card is not None
    assert card.report.id == created.report_id
    assert card.report.meal_type == "dinner"
    assert card.report.client_comment == "Курица и овощи"
    assert card.photo.telegram_file_id == "telegram-file-id-123"
    assert card.client.display_name == "Test Client"
    assert card.client_user.telegram_id == 2001


async def test_coach_cannot_open_other_coach_meal_report(session_factory):
    async with session_factory() as session:
        coach_user_1, coach_1 = await create_coach(session, telegram_id=1001)
        client_user_1, client_1, relation_1 = await create_client_for_coach(
            session,
            coach=coach_1,
            telegram_id=2001,
            display_name="Client One",
        )

        coach_user_2, coach_2 = await create_coach(session, telegram_id=1002)
        client_user_2, client_2, relation_2 = await create_client_for_coach(
            session,
            coach=coach_2,
            telegram_id=2002,
            display_name="Client Two",
        )

        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    assert created.ok is True

    card = await get_meal_report_for_coach(
        telegram_id=1002,
        report_id=created.report_id,
        session_factory=session_factory,
    )

    assert card is None


async def test_coach_can_review_own_meal_report(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    assert created.ok is True

    result = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="ok",
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.client_telegram_id == 2001
    assert result.client_display_name == "Test Client"
    assert result.verdict == "ok"
    assert result.report_status == "reviewed"

    async with session_factory() as session:
        report_result = await session.execute(
            select(MealReport).where(MealReport.id == created.report_id)
        )
        report = report_result.scalar_one()

        assert report.status == "reviewed"
        assert report.reviewed_at is not None

        review_result = await session.execute(
            select(MealReview).where(MealReview.report_id == created.report_id)
        )
        review = review_result.scalar_one()

        assert review.verdict == "ok"
        assert review.coach_id == coach.id


async def test_coach_can_mark_report_as_needs_clarification(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="snack",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    result = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="question",
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.report_status == "needs_clarification"

    async with session_factory() as session:
        report_result = await session.execute(
            select(MealReport).where(MealReport.id == created.report_id)
        )
        report = report_result.scalar_one()

        assert report.status == "needs_clarification"


async def test_coach_cannot_review_other_coach_report(session_factory):
    async with session_factory() as session:
        coach_user_1, coach_1 = await create_coach(session, telegram_id=1001)
        client_user_1, client_1, relation_1 = await create_client_for_coach(
            session,
            coach=coach_1,
            telegram_id=2001,
            display_name="Client One",
        )

        coach_user_2, coach_2 = await create_coach(session, telegram_id=1002)
        client_user_2, client_2, relation_2 = await create_client_for_coach(
            session,
            coach=coach_2,
            telegram_id=2002,
            display_name="Client Two",
        )

        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    result = await review_meal_report(
        telegram_id=1002,
        report_id=created.report_id,
        verdict="ok",
        session_factory=session_factory,
    )

    assert result.ok is False
    assert result.reason == "report_not_found"


async def test_report_cannot_be_reviewed_twice(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    first = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="ok",
        session_factory=session_factory,
    )

    second = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="needs_improvement",
        session_factory=session_factory,
    )

    assert first.ok is True
    assert second.ok is False
    assert second.reason == "report_already_reviewed"

async def test_coach_can_review_report_with_comment(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    assert created.ok is True

    result = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="needs_improvement",
        comment="Добавь больше белка и овощей.",
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.verdict == "needs_improvement"
    assert result.report_status == "reviewed"
    assert result.comment == "Добавь больше белка и овощей."

    async with session_factory() as session:
        review_result = await session.execute(
            select(MealReview).where(MealReview.report_id == created.report_id)
        )
        review = review_result.scalar_one()

        assert review.verdict == "needs_improvement"
        assert review.comment == "Добавь больше белка и овощей."

        report_result = await session.execute(
            select(MealReport).where(MealReport.id == created.report_id)
        )
        report = report_result.scalar_one()

        assert report.status == "reviewed"
        assert report.reviewed_at is not None

async def test_coach_can_ask_question_with_comment(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="dinner",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    result = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="question",
        comment="Что было в соусе?",
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.verdict == "question"
    assert result.report_status == "needs_clarification"
    assert result.comment == "Что было в соусе?"

    async with session_factory() as session:
        review_result = await session.execute(
            select(MealReview).where(MealReview.report_id == created.report_id)
        )
        review = review_result.scalar_one()

        assert review.verdict == "question"
        assert review.comment == "Что было в соусе?"

        report_result = await session.execute(
            select(MealReport).where(MealReport.id == created.report_id)
        )
        report = report_result.scalar_one()

        assert report.status == "needs_clarification"

async def test_client_can_list_own_meal_reports(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    assert created.ok is True

    reports = await list_meal_reports_for_client(
        telegram_id=2001,
        session_factory=session_factory,
    )

    assert len(reports) == 1
    assert reports[0].id == created.report_id
    assert reports[0].meal_type == "lunch"
    assert reports[0].status == "submitted"


async def test_client_cannot_list_other_client_reports(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)

        client_user_1, client_1, relation_1 = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Client One",
        )

        client_user_2, client_2, relation_2 = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2002,
            display_name="Client Two",
        )

        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    assert created.ok is True

    reports_1 = await list_meal_reports_for_client(
        telegram_id=2001,
        session_factory=session_factory,
    )

    reports_2 = await list_meal_reports_for_client(
        telegram_id=2002,
        session_factory=session_factory,
    )

    assert len(reports_1) == 1
    assert len(reports_2) == 0


async def test_client_can_open_own_meal_report(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="dinner",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        client_comment="Курица и овощи",
        session_factory=session_factory,
    )

    card = await get_meal_report_for_client(
        telegram_id=2001,
        report_id=created.report_id,
        session_factory=session_factory,
    )

    assert card is not None
    assert card.report.id == created.report_id
    assert card.report.meal_type == "dinner"
    assert card.report.client_comment == "Курица и овощи"
    assert card.photo.telegram_file_id == "telegram-file-id-123"
    assert card.review is None


async def test_client_cannot_open_other_client_report(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)

        client_user_1, client_1, relation_1 = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Client One",
        )

        client_user_2, client_2, relation_2 = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2002,
            display_name="Client Two",
        )

        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    card = await get_meal_report_for_client(
        telegram_id=2002,
        report_id=created.report_id,
        session_factory=session_factory,
    )

    assert card is None


async def test_client_can_see_review_comment(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    reviewed = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="needs_improvement",
        comment="Добавь больше белка.",
        session_factory=session_factory,
    )

    assert reviewed.ok is True

    card = await get_meal_report_for_client(
        telegram_id=2001,
        report_id=created.report_id,
        session_factory=session_factory,
    )

    assert card is not None
    assert card.report.status == "reviewed"
    assert card.review is not None
    assert card.review.verdict == "needs_improvement"
    assert card.review.comment == "Добавь больше белка."


async def test_inactive_client_cannot_list_meal_reports(session_factory):
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

    reports = await list_meal_reports_for_client(
        telegram_id=2001,
        session_factory=session_factory,
    )

    assert reports == []


async def test_report_can_have_multiple_reviews_after_client_clarification(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    first_review = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="question",
        comment="Что было в соусе?",
        session_factory=session_factory,
    )

    assert first_review.ok is True
    assert first_review.report_status == "needs_clarification"

    response = await respond_to_meal_report_clarification(
        telegram_id=2001,
        report_id=created.report_id,
        response_text="Это был йогуртовый соус.",
        session_factory=session_factory,
    )

    assert response.ok is True

    second_review = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="ok",
        comment=None,
        session_factory=session_factory,
    )

    assert second_review.ok is True
    assert second_review.report_status == "reviewed"

    async with session_factory() as session:
        reviews_result = await session.execute(
            select(MealReview)
            .where(MealReview.report_id == created.report_id)
            .order_by(MealReview.created_at.asc())
        )
        reviews = reviews_result.scalars().all()

        assert len(reviews) == 2
        assert reviews[0].verdict == "question"
        assert reviews[0].comment == "Что было в соусе?"
        assert reviews[1].verdict == "ok"

        report_result = await session.execute(
            select(MealReport).where(MealReport.id == created.report_id)
        )
        report = report_result.scalar_one()

        assert report.status == "reviewed"
        assert report.clarification_response == "Это был йогуртовый соус."


async def test_client_can_respond_to_meal_report_clarification(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    reviewed = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="question",
        comment="Что было в соусе?",
        session_factory=session_factory,
    )

    assert reviewed.ok is True
    assert reviewed.report_status == "needs_clarification"

    response = await respond_to_meal_report_clarification(
        telegram_id=2001,
        report_id=created.report_id,
        response_text="Это был йогуртовый соус.",
        session_factory=session_factory,
    )

    assert response.ok is True
    assert response.coach_telegram_id == 1001
    assert response.client_display_name == "Test Client"

    async with session_factory() as session:
        report_result = await session.execute(
            select(MealReport).where(MealReport.id == created.report_id)
        )
        report = report_result.scalar_one()

        assert report.status == "submitted"
        assert report.clarification_response == "Это был йогуртовый соус."
        assert report.clarification_responded_at is not None

        review_result = await session.execute(
            select(MealReview).where(MealReview.report_id == created.report_id)
        )
        reviews = review_result.scalars().all()

        assert len(reviews) == 1
        assert reviews[0].verdict == "question"


async def test_client_cannot_respond_to_other_client_clarification(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)

        client_user_1, client_1, relation_1 = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Client One",
        )
        client_user_2, client_2, relation_2 = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2002,
            display_name="Client Two",
        )

        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    reviewed = await review_meal_report(
        telegram_id=1001,
        report_id=created.report_id,
        verdict="question",
        comment="Что было в соусе?",
        session_factory=session_factory,
    )

    assert reviewed.ok is True

    response = await respond_to_meal_report_clarification(
        telegram_id=2002,
        report_id=created.report_id,
        response_text="Чужой ответ.",
        session_factory=session_factory,
    )

    assert response.ok is False
    assert response.reason == "report_not_found"


async def test_client_cannot_respond_when_report_is_not_waiting_for_clarification(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )
        await session.commit()

    created = await create_meal_report_from_photo(
        telegram_id=2001,
        meal_type="lunch",
        telegram_file_id="telegram-file-id-123",
        telegram_file_unique_id="telegram-unique-id-123",
        session_factory=session_factory,
    )

    response = await respond_to_meal_report_clarification(
        telegram_id=2001,
        report_id=created.report_id,
        response_text="Ответ.",
        session_factory=session_factory,
    )

    assert response.ok is False
    assert response.reason == "report_not_waiting_for_clarification"
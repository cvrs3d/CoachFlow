from datetime import UTC, datetime

from app.db.models import (
    MealReport,
    MealReview,
)
from app.services.dashboard import get_coach_dashboard
from tests.factories.entities import (
    create_client_for_coach,
    create_coach,
)


async def test_coach_dashboard_empty_state(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        await session.commit()

    result = await get_coach_dashboard(
        telegram_id=1001,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.stats is not None
    assert result.stats.today_appointments_count == 0
    assert result.stats.today_new_meal_reports_count == 0
    assert result.stats.pending_meal_reports_count == 0
    assert result.stats.waiting_clarification_count == 0
    assert result.stats.reports_7d_count == 0
    assert result.stats.reviewed_7d_count == 0
    assert result.stats.needs_improvement_7d_count == 0
    assert result.stats.active_clients_count == 0


async def test_dashboard_counts_active_clients(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)

        await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Client One",
        )
        await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2002,
            display_name="Client Two",
        )

        await session.commit()

    result = await get_coach_dashboard(
        telegram_id=1001,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.stats is not None
    assert result.stats.active_clients_count == 2


async def test_dashboard_counts_meal_reports(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Client One",
        )

        now = datetime.now(UTC)

        submitted_report = MealReport(
            id="report-submitted",
            checkin_id=None,
            client_id=client.id,
            coach_id=coach.id,
            meal_type="lunch",
            status="submitted",
            client_comment=None,
            submitted_at=now,
            reviewed_at=None,
        )

        clarification_report = MealReport(
            id="report-clarification",
            checkin_id=None,
            client_id=client.id,
            coach_id=coach.id,
            meal_type="dinner",
            status="needs_clarification",
            client_comment=None,
            submitted_at=now,
            reviewed_at=None,
        )

        reviewed_report = MealReport(
            id="report-reviewed",
            checkin_id=None,
            client_id=client.id,
            coach_id=coach.id,
            meal_type="breakfast",
            status="reviewed",
            client_comment=None,
            submitted_at=now,
            reviewed_at=now,
        )

        session.add_all(
            [
                submitted_report,
                clarification_report,
                reviewed_report,
            ]
        )
        await session.flush()

        review = MealReview(
            id="review-1",
            report_id=reviewed_report.id,
            coach_id=coach.id,
            verdict="needs_improvement",
            rating=None,
            comment="Add protein",
            created_at=now,
        )
        session.add(review)

        await session.commit()

    result = await get_coach_dashboard(
        telegram_id=1001,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.stats is not None

    assert result.stats.today_new_meal_reports_count == 3
    assert result.stats.pending_meal_reports_count == 1
    assert result.stats.waiting_clarification_count == 1
    assert result.stats.reports_7d_count == 3
    assert result.stats.reviewed_7d_count == 1
    assert result.stats.needs_improvement_7d_count == 1


async def test_dashboard_does_not_count_other_coach_data(session_factory):
    async with session_factory() as session:
        coach_user_1, coach_1 = await create_coach(session, telegram_id=1001)
        client_user_1, client_1, relation_1 = await create_client_for_coach(
            session,
            coach=coach_1,
            telegram_id=2001,
        )

        coach_user_2, coach_2 = await create_coach(session, telegram_id=1002)
        client_user_2, client_2, relation_2 = await create_client_for_coach(
            session,
            coach=coach_2,
            telegram_id=2002,
        )

        now = datetime.now(UTC)

        own_report = MealReport(
            id="own-report",
            checkin_id=None,
            client_id=client_1.id,
            coach_id=coach_1.id,
            meal_type="lunch",
            status="submitted",
            client_comment=None,
            submitted_at=now,
            reviewed_at=None,
        )

        other_report = MealReport(
            id="other-report",
            checkin_id=None,
            client_id=client_2.id,
            coach_id=coach_2.id,
            meal_type="lunch",
            status="submitted",
            client_comment=None,
            submitted_at=now,
            reviewed_at=None,
        )

        session.add_all([own_report, other_report])
        await session.commit()

    result = await get_coach_dashboard(
        telegram_id=1001,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.stats is not None
    assert result.stats.today_new_meal_reports_count == 1
    assert result.stats.pending_meal_reports_count == 1


async def test_dashboard_returns_coach_not_found_for_client(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
        )
        await session.commit()

    result = await get_coach_dashboard(
        telegram_id=2001,
        session_factory=session_factory,
    )

    assert result.ok is False
    assert result.reason == "coach_not_found"
    assert result.stats is None

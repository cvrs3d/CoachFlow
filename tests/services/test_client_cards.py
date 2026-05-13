from datetime import UTC, datetime, timedelta

from app.db.models import (
    Appointment,
    AvailabilitySlot,
    MealReport,
    MealReview,
)
from app.services.client_cards import get_client_card_for_coach
from tests.factories.entities import (
    create_client_for_coach,
    create_coach,
)


async def test_coach_can_get_client_card_empty_state(session_factory):
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

    result = await get_client_card_for_coach(
        coach_telegram_id=1001,
        client_id=client_id,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.card is not None

    assert result.card.client.id == client_id
    assert result.card.client.display_name == "Test Client"
    assert result.card.user.telegram_id == 2001
    assert result.card.upcoming_appointment is None

    assert result.card.stats.reports_7d_count == 0
    assert result.card.stats.reviewed_7d_count == 0
    assert result.card.stats.needs_improvement_7d_count == 0
    assert result.card.stats.waiting_clarification_count == 0


async def test_client_card_counts_upcoming_appointment(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )

        starts_at = datetime.now(UTC) + timedelta(days=1)
        ends_at = starts_at + timedelta(hours=1)

        slot = AvailabilitySlot(
            id="slot-1",
            coach_id=coach.id,
            starts_at=starts_at,
            ends_at=ends_at,
            status="booked",
            booked_by_client_id=client.id,
            booked_at=datetime.now(UTC),
        )
        session.add(slot)
        await session.flush()

        appointment = Appointment(
            id="appointment-1",
            slot_id=slot.id,
            coach_id=coach.id,
            client_id=client.id,
            status="booked",
            reminder_24h_sent_at=None,
        )
        session.add(appointment)

        await session.commit()

        client_id = client.id

    result = await get_client_card_for_coach(
        coach_telegram_id=1001,
        client_id=client_id,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.card is not None
    assert result.card.upcoming_appointment is not None
    assert result.card.upcoming_appointment.appointment_id == "appointment-1"
    assert result.card.upcoming_appointment.slot_id == "slot-1"


async def test_client_card_counts_food_report_stats(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
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
            clarification_response=None,
            clarification_responded_at=None,
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
            clarification_response=None,
            clarification_responded_at=None,
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
            clarification_response=None,
            clarification_responded_at=None,
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
            comment="More protein",
            created_at=now,
        )
        session.add(review)

        await session.commit()

        client_id = client.id

    result = await get_client_card_for_coach(
        coach_telegram_id=1001,
        client_id=client_id,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.card is not None

    assert result.card.stats.reports_7d_count == 3
    assert result.card.stats.reviewed_7d_count == 1
    assert result.card.stats.needs_improvement_7d_count == 1
    assert result.card.stats.waiting_clarification_count == 1


async def test_coach_cannot_get_other_coach_client_card(session_factory):
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

        other_client_id = client_2.id

    result = await get_client_card_for_coach(
        coach_telegram_id=1001,
        client_id=other_client_id,
        session_factory=session_factory,
    )

    assert result.ok is False
    assert result.reason == "client_not_found"
    assert result.card is None


async def test_client_cannot_get_client_card(session_factory):
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

    result = await get_client_card_for_coach(
        coach_telegram_id=2001,
        client_id=client_id,
        session_factory=session_factory,
    )

    assert result.ok is False
    assert result.reason == "coach_not_found"
    assert result.card is None

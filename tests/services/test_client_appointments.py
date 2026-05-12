from datetime import datetime, timedelta, timezone

from app.db.models import Appointment, AvailabilitySlot
from app.services.client_appointments import list_client_appointments_for_coach
from tests.factories.entities import create_client_for_coach, create_coach


async def test_coach_can_list_client_future_appointments(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )

        starts_at = datetime.now(timezone.utc) + timedelta(days=1)
        ends_at = starts_at + timedelta(hours=1)

        slot = AvailabilitySlot(
            id="slot-future-1",
            coach_id=coach.id,
            starts_at=starts_at,
            ends_at=ends_at,
            status="booked",
            booked_by_client_id=client.id,
            booked_at=datetime.now(timezone.utc),
        )
        session.add(slot)
        await session.flush()

        appointment = Appointment(
            id="appointment-future-1",
            slot_id=slot.id,
            coach_id=coach.id,
            client_id=client.id,
            status="booked",
            reminder_24h_sent_at=None,
        )
        session.add(appointment)

        await session.commit()

        client_id = client.id

    result = await list_client_appointments_for_coach(
        coach_telegram_id=1001,
        client_id=client_id,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.client is not None
    assert result.client.display_name == "Test Client"
    assert result.future_items is not None
    assert len(result.future_items) == 1
    assert result.future_items[0].appointment.id == "appointment-future-1"
    assert result.future_items[0].slot.id == "slot-future-1"

    assert result.history_items == []


async def test_coach_can_list_client_appointment_history(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )

        starts_at = datetime.now(timezone.utc) - timedelta(days=1)
        ends_at = starts_at + timedelta(hours=1)

        slot = AvailabilitySlot(
            id="slot-history-1",
            coach_id=coach.id,
            starts_at=starts_at,
            ends_at=ends_at,
            status="booked",
            booked_by_client_id=client.id,
            booked_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(slot)
        await session.flush()

        appointment = Appointment(
            id="appointment-history-1",
            slot_id=slot.id,
            coach_id=coach.id,
            client_id=client.id,
            status="booked",
            reminder_24h_sent_at=None,
        )
        session.add(appointment)

        await session.commit()

        client_id = client.id

    result = await list_client_appointments_for_coach(
        coach_telegram_id=1001,
        client_id=client_id,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.future_items == []
    assert result.history_items is not None
    assert len(result.history_items) == 1
    assert result.history_items[0].appointment.id == "appointment-history-1"


async def test_coach_can_list_cancelled_client_appointments_in_history(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )

        starts_at = datetime.now(timezone.utc) + timedelta(days=1)
        ends_at = starts_at + timedelta(hours=1)

        slot = AvailabilitySlot(
            id="slot-cancelled-1",
            coach_id=coach.id,
            starts_at=starts_at,
            ends_at=ends_at,
            status="available",
            booked_by_client_id=None,
            booked_at=None,
        )
        session.add(slot)
        await session.flush()

        appointment = Appointment(
            id="appointment-cancelled-1",
            slot_id=slot.id,
            coach_id=coach.id,
            client_id=client.id,
            status="cancelled_by_client",
            reminder_24h_sent_at=None,
        )
        session.add(appointment)

        await session.commit()

        client_id = client.id

    result = await list_client_appointments_for_coach(
        coach_telegram_id=1001,
        client_id=client_id,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.future_items == []
    assert result.history_items is not None
    assert len(result.history_items) == 1
    assert result.history_items[0].appointment.status == "cancelled_by_client"


async def test_coach_cannot_list_other_coach_client_appointments(session_factory):
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

        await session.commit()

        client_2_id = client_2.id

    result = await list_client_appointments_for_coach(
        coach_telegram_id=1001,
        client_id=client_2_id,
        session_factory=session_factory,
    )

    assert result.ok is False
    assert result.reason == "client_not_found"


async def test_client_cannot_list_client_appointments_as_coach(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
        )

        await session.commit()

        client_id = client.id

    result = await list_client_appointments_for_coach(
        coach_telegram_id=2001,
        client_id=client_id,
        session_factory=session_factory,
    )

    assert result.ok is False
    assert result.reason == "coach_not_found"
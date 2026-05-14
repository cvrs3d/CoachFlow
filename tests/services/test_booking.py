from sqlalchemy import select

from app.db.models import Appointment, AvailabilitySlot
from app.services.booking import book_slot_for_client
from app.services.client_bookings import cancel_booking_by_client
from tests.factories.entities import (
    create_available_slot,
    create_client_for_coach,
    create_coach,
)


async def test_client_can_book_available_slot(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
        )
        slot = await create_available_slot(session, coach=coach)

        await session.commit()

        slot_id = slot.id

    result = await book_slot_for_client(
        telegram_id=2001,
        slot_id=slot_id,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.reason is None
    assert result.appointment_id is not None

    async with session_factory() as session:
        slot_result = await session.execute(
            select(AvailabilitySlot).where(AvailabilitySlot.id == slot_id)
        )
        updated_slot = slot_result.scalar_one()

        assert updated_slot.status == "booked"
        assert updated_slot.booked_by_client_id == client.id
        assert updated_slot.booked_at is not None

        appointment_result = await session.execute(
            select(Appointment).where(Appointment.slot_id == slot_id)
        )
        appointment = appointment_result.scalar_one()

        assert appointment.status == "booked"
        assert appointment.client_id == client.id
        assert appointment.coach_id == coach.id


async def test_cannot_book_already_booked_slot(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
        )
        slot = await create_available_slot(session, coach=coach)
        await session.commit()

        slot_id = slot.id

    first = await book_slot_for_client(
        telegram_id=2001,
        slot_id=slot_id,
        session_factory=session_factory,
    )

    second = await book_slot_for_client(
        telegram_id=2001,
        slot_id=slot_id,
        session_factory=session_factory,
    )

    assert first.ok is True
    assert second.ok is False
    assert second.reason == "slot_not_available"


async def test_client_can_rebook_same_slot_after_cancellation(session_factory):
    async with session_factory() as session:
        coach_user, coach = await create_coach(session, telegram_id=1001)
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
        )
        slot = await create_available_slot(session, coach=coach, starts_in_hours=72)
        await session.commit()

        slot_id = slot.id

    first_booking = await book_slot_for_client(
        telegram_id=2001,
        slot_id=slot_id,
        session_factory=session_factory,
    )

    assert first_booking.ok is True

    cancel_result = await cancel_booking_by_client(
        telegram_id=2001,
        appointment_id=first_booking.appointment_id,
        session_factory=session_factory,
    )

    assert cancel_result.ok is True

    second_booking = await book_slot_for_client(
        telegram_id=2001,
        slot_id=slot_id,
        session_factory=session_factory,
    )

    assert second_booking.ok is True

    async with session_factory() as session:
        appointments_result = await session.execute(
            select(Appointment).where(Appointment.slot_id == slot_id)
        )
        appointments = appointments_result.scalars().all()

        assert len(appointments) == 1
        assert appointments[0].status == "booked"

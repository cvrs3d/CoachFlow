from datetime import UTC, datetime, timedelta

from app.db.models import Appointment, AvailabilitySlot
from app.services.calendar_files import (
    build_client_appointment_ics,
    build_client_future_bookings_ics,
    build_coach_future_bookings_ics,
)
from tests.factories.entities import create_client_for_coach, create_coach


FUTURE_START_1 = datetime(2030, 6, 14, 12, 0, tzinfo=UTC)
FUTURE_START_2 = datetime(2030, 6, 15, 8, 30, tzinfo=UTC)


async def _create_booked_appointment(
    session,
    *,
    coach,
    client,
    appointment_id: str = "appointment-1",
    slot_id: str = "slot-1",
    starts_at: datetime | None = None,
    duration_minutes: int = 60,
) -> tuple[Appointment, AvailabilitySlot]:
    starts_at = starts_at or FUTURE_START_1
    ends_at = starts_at + timedelta(minutes=duration_minutes)

    slot = AvailabilitySlot(
        id=slot_id,
        coach_id=coach.id,
        starts_at=starts_at,
        ends_at=ends_at,
        status="booked",
        booked_by_client_id=client.id,
        booked_at=datetime(2030, 6, 13, 10, 0, tzinfo=UTC),
    )
    session.add(slot)
    await session.flush()

    appointment = Appointment(
        id=appointment_id,
        slot_id=slot.id,
        coach_id=coach.id,
        client_id=client.id,
        status="booked",
        reminder_24h_sent_at=None,
    )
    session.add(appointment)
    await session.flush()

    return appointment, slot


async def test_client_appointment_ics_contains_utc_dates_uid_and_local_description(
    session_factory,
):
    async with session_factory() as session:
        coach_user, coach = await create_coach(
            session,
            telegram_id=1001,
            timezone_name="Europe/Prague",
        )
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )

        await _create_booked_appointment(
            session,
            coach=coach,
            client=client,
            appointment_id="appointment-123",
            slot_id="slot-123",
            starts_at=FUTURE_START_1,
        )

        await session.commit()

    result = await build_client_appointment_ics(
        telegram_id=2001,
        appointment_id="appointment-123",
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.filename == "coachflow_appointment.ics"
    assert result.file_bytes is not None

    ics_text = result.file_bytes.decode("utf-8")

    assert "BEGIN:VCALENDAR" in ics_text
    assert "BEGIN:VEVENT" in ics_text
    assert "UID:appointment-123@coachflow" in ics_text

    assert "DTSTART:20300614T120000Z" in ics_text
    assert "DTEND:20300614T130000Z" in ics_text

    assert "Время: 14.06.2030 14:00–15:00" in ics_text
    assert "Часовой пояс: Europe/Prague" in ics_text


async def test_client_future_bookings_ics_contains_all_future_booked_appointments(
    session_factory,
):
    async with session_factory() as session:
        coach_user, coach = await create_coach(
            session,
            telegram_id=1001,
            timezone_name="Europe/Prague",
        )
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Test Client",
        )

        await _create_booked_appointment(
            session,
            coach=coach,
            client=client,
            appointment_id="appointment-1",
            slot_id="slot-1",
            starts_at=FUTURE_START_1,
        )
        await _create_booked_appointment(
            session,
            coach=coach,
            client=client,
            appointment_id="appointment-2",
            slot_id="slot-2",
            starts_at=FUTURE_START_2,
        )

        await session.commit()

    result = await build_client_future_bookings_ics(
        telegram_id=2001,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.filename == "coachflow_my_bookings.ics"
    assert result.file_bytes is not None

    ics_text = result.file_bytes.decode("utf-8")

    assert "UID:appointment-1@coachflow" in ics_text
    assert "UID:appointment-2@coachflow" in ics_text

    assert "DTSTART:20300614T120000Z" in ics_text
    assert "DTEND:20300614T130000Z" in ics_text

    assert "DTSTART:20300615T083000Z" in ics_text
    assert "DTEND:20300615T093000Z" in ics_text

    assert "Время: 14.06.2030 14:00–15:00" in ics_text
    assert "Время: 15.06.2030 10:30–11:30" in ics_text


async def test_coach_future_bookings_ics_uses_coach_timezone_in_description(
    session_factory,
):
    async with session_factory() as session:
        coach_user, coach = await create_coach(
            session,
            telegram_id=1001,
            timezone_name="Europe/Prague",
        )
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Ivan Client",
        )

        await _create_booked_appointment(
            session,
            coach=coach,
            client=client,
            appointment_id="coach-appointment-1",
            slot_id="coach-slot-1",
            starts_at=FUTURE_START_1,
        )

        await session.commit()

    result = await build_coach_future_bookings_ics(
        telegram_id=1001,
        session_factory=session_factory,
    )

    assert result.ok is True
    assert result.filename == "coachflow_coach_bookings.ics"
    assert result.file_bytes is not None

    ics_text = result.file_bytes.decode("utf-8")

    assert "UID:coach-appointment-1@coachflow" in ics_text
    assert "SUMMARY:Тренировка: Ivan Client" in ics_text

    assert "DTSTART:20300614T120000Z" in ics_text
    assert "DTEND:20300614T130000Z" in ics_text

    assert "Клиент: Ivan Client" in ics_text
    assert "Время: 14.06.2030 14:00–15:00" in ics_text
    assert "Часовой пояс: Europe/Prague" in ics_text


async def test_client_appointment_ics_returns_not_found_for_other_client(
    session_factory,
):
    async with session_factory() as session:
        coach_user, coach = await create_coach(
            session,
            telegram_id=1001,
            timezone_name="Europe/Prague",
        )
        client_user, client, relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=2001,
            display_name="Owner Client",
        )
        other_client_user, other_client, other_relation = await create_client_for_coach(
            session,
            coach=coach,
            telegram_id=3001,
            display_name="Other Client",
        )

        await _create_booked_appointment(
            session,
            coach=coach,
            client=client,
            appointment_id="private-appointment",
            slot_id="private-slot",
            starts_at=FUTURE_START_1,
        )

        await session.commit()

    result = await build_client_appointment_ics(
        telegram_id=3001,
        appointment_id="private-appointment",
        session_factory=session_factory,
    )

    assert result.ok is False
    assert result.reason == "appointment_not_found"
    assert result.file_bytes is None
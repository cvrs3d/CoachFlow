import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Appointment, AvailabilitySlot, Client, Coach, User
from app.utils.datetime import ensure_utc, format_slot_range_for_timezone


@dataclass
class CalendarFileResult:
    ok: bool
    reason: str | None = None
    filename: str | None = None
    file_bytes: bytes | None = None


@dataclass
class CalendarEvent:
    uid: str
    starts_at: datetime
    ends_at: datetime
    summary: str
    description: str
    status: str = "CONFIRMED"


def _ics_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _ics_dt_utc(value: datetime) -> str:
    utc_value = ensure_utc(value).astimezone(UTC)
    return utc_value.strftime("%Y%m%dT%H%M%SZ")


def _build_calendar(events: list[CalendarEvent], calendar_name: str) -> str:
    now = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//CoachFlow//Telegram Bot//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_ics_escape(calendar_name)}",
    ]

    for event in events:
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{_ics_escape(event.uid)}",
                f"DTSTAMP:{now}",
                f"DTSTART:{_ics_dt_utc(event.starts_at)}",
                f"DTEND:{_ics_dt_utc(event.ends_at)}",
                f"SUMMARY:{_ics_escape(event.summary)}",
                f"DESCRIPTION:{_ics_escape(event.description)}",
                f"STATUS:{event.status}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")

    return "\r\n".join(lines) + "\r\n"


def _appointment_uid(appointment_id: str) -> str:
    return f"{appointment_id}@coachflow"


async def build_client_appointment_ics(
    *,
    telegram_id: int,
    appointment_id: str,
    session_factory=AsyncSessionLocal,
) -> CalendarFileResult:
    async with session_factory() as session:
        result = await session.execute(
            select(Appointment, AvailabilitySlot, Client, Coach)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .join(Client, Appointment.client_id == Client.id)
            .join(Coach, Appointment.coach_id == Coach.id)
            .join(User, Client.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(Appointment.id == appointment_id)
            .where(Appointment.status == "booked")
        )
        row = result.one_or_none()

        if row is None:
            return CalendarFileResult(ok=False, reason="appointment_not_found")

        appointment, slot, client, coach = row

        # Пока у клиента нет своего timezone в модели.
        # Поэтому для клиента используем timezone тренера.
        timezone_name = coach.timezone or "Europe/Prague"
        slot_time = format_slot_range_for_timezone(
            slot.starts_at,
            slot.ends_at,
            timezone_name,
        )

        event = CalendarEvent(
            uid=_appointment_uid(appointment.id),
            starts_at=slot.starts_at,
            ends_at=slot.ends_at,
            summary="Тренировка",
            description=(
                "Запись в CoachFlow\n"
                f"Время: {slot_time}\n"
                f"Часовой пояс: {timezone_name}"
            ),
        )

        ics_text = _build_calendar([event], "CoachFlow · Моя запись")

        return CalendarFileResult(
            ok=True,
            filename="coachflow_appointment.ics",
            file_bytes=ics_text.encode("utf-8"),
        )


async def build_client_future_bookings_ics(
    *,
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> CalendarFileResult:
    async with session_factory() as session:
        now = datetime.now(UTC)

        result = await session.execute(
            select(Appointment, AvailabilitySlot, Client, Coach)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .join(Client, Appointment.client_id == Client.id)
            .join(Coach, Appointment.coach_id == Coach.id)
            .join(User, Client.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(Appointment.status == "booked")
            .where(AvailabilitySlot.starts_at >= now)
            .order_by(AvailabilitySlot.starts_at.asc())
        )

        rows = list(result.all())

        if not rows:
            return CalendarFileResult(ok=False, reason="no_future_bookings")

        events = []

        for appointment, slot, client, coach in rows:
            timezone_name = coach.timezone or "Europe/Prague"
            slot_time = format_slot_range_for_timezone(
                slot.starts_at,
                slot.ends_at,
                timezone_name,
            )

            events.append(
                CalendarEvent(
                    uid=_appointment_uid(appointment.id),
                    starts_at=slot.starts_at,
                    ends_at=slot.ends_at,
                    summary="Тренировка",
                    description=(
                        "Запись в CoachFlow\n"
                        f"Время: {slot_time}\n"
                        f"Часовой пояс: {timezone_name}"
                    ),
                )
            )

        ics_text = _build_calendar(events, "CoachFlow · Мои записи")

        return CalendarFileResult(
            ok=True,
            filename="coachflow_my_bookings.ics",
            file_bytes=ics_text.encode("utf-8"),
        )


async def build_coach_future_bookings_ics(
    *,
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> CalendarFileResult:
    async with session_factory() as session:
        now = datetime.now(UTC)

        coach_result = await session.execute(
            select(Coach, User)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )
        coach_row = coach_result.one_or_none()

        if coach_row is None:
            return CalendarFileResult(ok=False, reason="coach_not_found")

        coach, coach_user = coach_row
        timezone_name = coach.timezone or "Europe/Prague"

        result = await session.execute(
            select(Appointment, AvailabilitySlot, Client)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .join(Client, Appointment.client_id == Client.id)
            .where(Appointment.coach_id == coach.id)
            .where(Appointment.status == "booked")
            .where(AvailabilitySlot.starts_at >= now)
            .order_by(AvailabilitySlot.starts_at.asc())
        )

        rows = list(result.all())

        if not rows:
            return CalendarFileResult(ok=False, reason="no_future_bookings")

        events = []

        for appointment, slot, client in rows:
            client_name = client.display_name or "без имени"
            slot_time = format_slot_range_for_timezone(
                slot.starts_at,
                slot.ends_at,
                timezone_name,
            )

            events.append(
                CalendarEvent(
                    uid=_appointment_uid(appointment.id),
                    starts_at=slot.starts_at,
                    ends_at=slot.ends_at,
                    summary=f"Тренировка: {client_name}",
                    description=(
                        "Занятие из CoachFlow\n"
                        f"Клиент: {client_name}\n"
                        f"Время: {slot_time}\n"
                        f"Часовой пояс: {timezone_name}"
                    ),
                )
            )

        ics_text = _build_calendar(events, "CoachFlow · Занятия тренера")

        return CalendarFileResult(
            ok=True,
            filename="coachflow_coach_bookings.ics",
            file_bytes=ics_text.encode("utf-8"),
        )


async def build_coach_slot_appointment_ics(
    *,
    telegram_id: int,
    slot_id: str,
    session_factory=AsyncSessionLocal,
) -> CalendarFileResult:
    async with session_factory() as session:
        result = await session.execute(
            select(Appointment, AvailabilitySlot, Client, Coach)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .join(Client, Appointment.client_id == Client.id)
            .join(Coach, Appointment.coach_id == Coach.id)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
            .where(AvailabilitySlot.id == slot_id)
            .where(Appointment.status == "booked")
        )
        row = result.one_or_none()

        if row is None:
            return CalendarFileResult(ok=False, reason="appointment_not_found")

        appointment, slot, client, coach = row

        timezone_name = coach.timezone or "Europe/Prague"
        client_name = client.display_name or "без имени"

        slot_time = format_slot_range_for_timezone(
            slot.starts_at,
            slot.ends_at,
            timezone_name,
        )

        event = CalendarEvent(
            uid=_appointment_uid(appointment.id),
            starts_at=slot.starts_at,
            ends_at=slot.ends_at,
            summary=f"Тренировка: {client_name}",
            description=(
                "Занятие из CoachFlow\n"
                f"Клиент: {client_name}\n"
                f"Время: {slot_time}\n"
                f"Часовой пояс: {timezone_name}"
            ),
        )

        ics_text = _build_calendar([event], "CoachFlow · Занятие")

        return CalendarFileResult(
            ok=True,
            filename="coachflow_appointment.ics",
            file_bytes=ics_text.encode("utf-8"),
        )
    
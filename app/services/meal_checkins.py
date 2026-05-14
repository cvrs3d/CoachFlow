import uuid
from dataclasses import dataclass
from datetime import datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import (
    Client,
    ClientCoachRelation,
    Coach,
    MealCheckin,
    MealCheckinSchedule,
    User,
)
from aiogram import Bot
from app.services.notifications import send_logged_message


DEFAULT_MEAL_SCHEDULES = [
    ("breakfast", "09:00"),
    ("lunch", "13:00"),
    ("dinner", "19:00"),
]

MEAL_TYPE_LABELS = {
    "breakfast": "завтрака",
    "lunch": "обеда",
    "dinner": "ужина",
    "snack": "перекуса",
    "other": "приема пищи",
}

@dataclass
class SendDueMealCheckinsResult:
    sent_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0

@dataclass
class EnsureDefaultMealSchedulesResult:
    ok: bool
    reason: str | None = None
    created_count: int = 0


@dataclass
class GenerateMealCheckinsResult:
    ok: bool
    reason: str | None = None
    created_count: int = 0

@dataclass
class MealCheckinScheduleListResult:
    ok: bool
    reason: str | None = None
    timezone_name: str | None = None
    schedules: list[MealCheckinSchedule] | None = None

async def ensure_default_meal_checkin_schedules_for_coach(
    *,
    coach_telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> EnsureDefaultMealSchedulesResult:
    async with session_factory() as session:
        coach_result = await session.execute(
            select(Coach, User)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == coach_telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )
        row = coach_result.one_or_none()

        if row is None:
            return EnsureDefaultMealSchedulesResult(
                ok=False,
                reason="coach_not_found",
            )

        coach, user = row
        created_count = 0

        for meal_type, local_time in DEFAULT_MEAL_SCHEDULES:
            existing_result = await session.execute(
                select(MealCheckinSchedule)
                .where(MealCheckinSchedule.coach_id == coach.id)
                .where(MealCheckinSchedule.meal_type == meal_type)
                .where(MealCheckinSchedule.local_time == local_time)
            )
            existing = existing_result.scalar_one_or_none()

            if existing is not None:
                continue

            schedule = MealCheckinSchedule(
                id=str(uuid.uuid4()),
                coach_id=coach.id,
                meal_type=meal_type,
                local_time=local_time,
                timezone=coach.timezone or "Europe/Prague",
                is_active=True,
            )
            session.add(schedule)
            created_count += 1

        await session.commit()

        return EnsureDefaultMealSchedulesResult(
            ok=True,
            created_count=created_count,
        )


async def generate_meal_checkins_for_coach_date(
    *,
    coach_telegram_id: int,
    target_date: datetime,
    session_factory=AsyncSessionLocal,
) -> GenerateMealCheckinsResult:
    """
    Создает pending MealCheckin для всех активных клиентов тренера
    на указанную дату по активным schedule rows.

    target_date можно передавать как datetime; используется только date() в timezone тренера.
    """

    async with session_factory() as session:
        coach_result = await session.execute(
            select(Coach, User)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == coach_telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )
        row = coach_result.one_or_none()

        if row is None:
            return GenerateMealCheckinsResult(
                ok=False,
                reason="coach_not_found",
            )

        coach, user = row
        coach_timezone = coach.timezone or "Europe/Prague"
        coach_tz = ZoneInfo(coach_timezone)

        local_date = target_date.astimezone(coach_tz).date()

        schedules_result = await session.execute(
            select(MealCheckinSchedule)
            .where(MealCheckinSchedule.coach_id == coach.id)
            .where(MealCheckinSchedule.is_active.is_(True))
        )
        schedules = list(schedules_result.scalars().all())

        clients_result = await session.execute(
            select(Client)
            .join(ClientCoachRelation, ClientCoachRelation.client_id == Client.id)
            .where(ClientCoachRelation.coach_id == coach.id)
            .where(ClientCoachRelation.status == "active")
            .where(Client.status == "active")
        )
        clients = list(clients_result.scalars().all())

        created_count = 0

        for client in clients:
            for schedule in schedules:
                scheduled_at = _local_datetime_to_utc(
                    local_date=local_date,
                    local_time=schedule.local_time,
                    timezone_name=schedule.timezone,
                )

                existing_result = await session.execute(
                    select(MealCheckin)
                    .where(MealCheckin.client_id == client.id)
                    .where(MealCheckin.coach_id == coach.id)
                    .where(MealCheckin.meal_type == schedule.meal_type)
                    .where(MealCheckin.scheduled_at == scheduled_at)
                )
                existing = existing_result.scalar_one_or_none()

                if existing is not None:
                    continue

                checkin = MealCheckin(
                    id=str(uuid.uuid4()),
                    client_id=client.id,
                    coach_id=coach.id,
                    meal_type=schedule.meal_type,
                    scheduled_at=scheduled_at,
                    status="pending",
                )
                session.add(checkin)
                created_count += 1

        await session.commit()

        return GenerateMealCheckinsResult(
            ok=True,
            created_count=created_count,
        )


def _local_datetime_to_utc(
    *,
    local_date,
    local_time: str,
    timezone_name: str,
) -> datetime:
    hour_text, minute_text = local_time.split(":", 1)

    local_dt = datetime.combine(
        local_date,
        time(
            hour=int(hour_text),
            minute=int(minute_text),
        ),
        tzinfo=ZoneInfo(timezone_name),
    )

    return local_dt.astimezone(timezone.utc)

async def list_meal_checkin_schedules_for_coach(
    *,
    coach_telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> MealCheckinScheduleListResult:
    async with session_factory() as session:
        coach_result = await session.execute(
            select(Coach, User)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == coach_telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )
        row = coach_result.one_or_none()

        if row is None:
            return MealCheckinScheduleListResult(
                ok=False,
                reason="coach_not_found",
            )

        coach, user = row

        schedules_result = await session.execute(
            select(MealCheckinSchedule)
            .where(MealCheckinSchedule.coach_id == coach.id)
            .where(MealCheckinSchedule.is_active.is_(True))
            .order_by(MealCheckinSchedule.local_time.asc())
        )

        return MealCheckinScheduleListResult(
            ok=True,
            timezone_name=coach.timezone or "Europe/Prague",
            schedules=list(schedules_result.scalars().all()),
        )
    
async def send_due_meal_checkin_requests(
    *,
    bot: Bot,
    lookback_minutes: int = 30,
    limit: int = 50,
    session_factory=AsyncSessionLocal,
) -> SendDueMealCheckinsResult:
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=lookback_minutes)

    result_summary = SendDueMealCheckinsResult()

    async with session_factory() as session:
        checkins_result = await session.execute(
            select(MealCheckin, Client, User, Coach)
            .join(Client, MealCheckin.client_id == Client.id)
            .join(User, Client.user_id == User.id)
            .join(Coach, MealCheckin.coach_id == Coach.id)
            .join(
                ClientCoachRelation,
                ClientCoachRelation.client_id == Client.id,
            )
            .where(ClientCoachRelation.coach_id == MealCheckin.coach_id)
            .where(ClientCoachRelation.status == "active")
            .where(Client.status == "active")
            .where(User.status == "active")
            .where(MealCheckin.status == "pending")
            .where(MealCheckin.scheduled_at <= now)
            .where(MealCheckin.scheduled_at >= window_start)
            .order_by(MealCheckin.scheduled_at.asc())
            .limit(limit)
        )

        rows = checkins_result.all()

        for checkin, client, user, coach in rows:
            meal_label = MEAL_TYPE_LABELS.get(checkin.meal_type, "приема пищи")

            send_result = await send_logged_message(
                bot=bot,
                chat_id=user.telegram_id,
                notification_type="meal_checkin_request",
                related_entity_type="meal_checkin",
                related_entity_id=checkin.id,
                text=(
                    f"Пора отправить фото {meal_label}.\n\n"
                    "Откройте “🍽 Отправить фото еды” и отправьте фото."
                ),
                session_factory=session_factory,
            )

            if send_result.ok:
                checkin.status = "sent"
                result_summary.sent_count += 1
            else:
                result_summary.failed_count += 1

        await session.commit()

    return result_summary
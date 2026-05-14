from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.db.database import AsyncSessionLocal, safe_commit
from app.db.models import Appointment, AvailabilitySlot, Client, ClientCoachRelation, Coach, User
from app.services.client_cards import get_client_card_for_coach


@dataclass
class ClientCard:
    client: Client
    user: User
    future_appointments_count: int


async def get_coach_by_telegram_id(
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> Coach | None:
    async with session_factory() as session:
        result = await session.execute(
            select(Coach)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )

        return result.scalar_one_or_none()


async def list_clients_for_coach(
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> list[Client]:
    async with session_factory() as session:
        coach_result = await session.execute(
            select(Coach)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )
        coach = coach_result.scalar_one_or_none()

        if coach is None:
            return []

        result = await session.execute(
            select(Client)
            .join(ClientCoachRelation, ClientCoachRelation.client_id == Client.id)
            .where(ClientCoachRelation.coach_id == coach.id)
            .where(ClientCoachRelation.status == "active")
            .where(Client.status == "active")
            .order_by(Client.display_name.asc())
        )

        return list(result.scalars().all())


async def get_client_card(
    *,
    telegram_id: int,
    client_id: str,
    session_factory=AsyncSessionLocal,
) -> ClientCard | None:
    async with session_factory() as session:
        coach_result = await session.execute(
            select(Coach)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )
        coach = coach_result.scalar_one_or_none()

        if coach is None:
            return None

        client_result = await session.execute(
            select(Client, User)
            .join(User, Client.user_id == User.id)
            .join(ClientCoachRelation, ClientCoachRelation.client_id == Client.id)
            .where(Client.id == client_id)
            .where(ClientCoachRelation.coach_id == coach.id)
            .where(ClientCoachRelation.status == "active")
        )

        row = client_result.one_or_none()

        if row is None:
            return None

        client, user = row

        count_result = await session.execute(
            select(func.count(Appointment.id))
            .where(Appointment.client_id == client.id)
            .where(Appointment.coach_id == coach.id)
            .where(Appointment.status == "booked")
        )

        future_appointments_count = count_result.scalar_one()

        return ClientCard(
            client=client,
            user=user,
            future_appointments_count=future_appointments_count,
        )


async def update_client_display_name_for_coach(
    *,
    telegram_id: int,
    client_id: str,
    new_display_name: str,
    session_factory=AsyncSessionLocal,
) -> bool:
    async with session_factory() as session:
        coach_result = await session.execute(
            select(Coach)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )
        coach = coach_result.scalar_one_or_none()

        if coach is None:
            return False

        client_result = await session.execute(
            select(Client)
            .join(ClientCoachRelation, ClientCoachRelation.client_id == Client.id)
            .where(Client.id == client_id)
            .where(ClientCoachRelation.coach_id == coach.id)
            .where(ClientCoachRelation.status == "active")
        )
        client = client_result.scalar_one_or_none()

        if client is None:
            return False

        client.display_name = new_display_name.strip()

        await safe_commit(session)
        return True


async def get_client_display_name_for_coach(
    *,
    telegram_id: int,
    client_id: str,
) -> str | None:
    card = await get_client_card_for_coach(
        telegram_id=telegram_id,
        client_id=client_id,
    )

    if card is None:
        return None

    return card.client.display_name


async def deactivate_client_for_coach(
    *,
    telegram_id: int,
    client_id: str,
    session_factory=AsyncSessionLocal,
) -> bool:
    async with session_factory() as session:
        coach_result = await session.execute(
            select(Coach)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )
        coach = coach_result.scalar_one_or_none()

        if coach is None:
            return False

        client_result = await session.execute(
            select(Client)
            .join(ClientCoachRelation, ClientCoachRelation.client_id == Client.id)
            .where(Client.id == client_id)
            .where(ClientCoachRelation.coach_id == coach.id)
            .where(ClientCoachRelation.status == "active")
        )
        client = client_result.scalar_one_or_none()

        if client is None:
            return False

        relation_result = await session.execute(
            select(ClientCoachRelation)
            .where(ClientCoachRelation.client_id == client.id)
            .where(ClientCoachRelation.coach_id == coach.id)
        )
        relation = relation_result.scalar_one_or_none()

        if relation is not None:
            relation.status = "inactive"

        client.status = "inactive"

        # Отменяем будущие записи клиента у этого тренера.
        appointments_result = await session.execute(
            select(Appointment, AvailabilitySlot)
            .join(AvailabilitySlot, Appointment.slot_id == AvailabilitySlot.id)
            .where(Appointment.client_id == client.id)
            .where(Appointment.coach_id == coach.id)
            .where(Appointment.status == "booked")
            .where(AvailabilitySlot.starts_at >= datetime.now(UTC))
        )

        rows = appointments_result.all()

        for appointment, slot in rows:
            appointment.status = "cancelled_by_coach"

            # Слот освобождаем, чтобы тренер мог отдать его другому клиенту.
            # Если хочешь при удалении клиента полностью убирать эти окна,
            # замени на slot.status = "cancelled".
            slot.status = "available"
            slot.booked_by_client_id = None
            slot.booked_at = None

        await safe_commit(session)
        return True

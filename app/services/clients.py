from dataclasses import dataclass

from sqlalchemy import func, select

from app.db.database import AsyncSessionLocal
from app.db.models import Appointment, Client, ClientCoachRelation, Coach, User


@dataclass
class ClientCard:
    client: Client
    user: User
    future_appointments_count: int


async def get_coach_by_telegram_id(telegram_id: int) -> Coach | None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Coach)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )

        return result.scalar_one_or_none()


async def list_clients_for_coach(telegram_id: int) -> list[Client]:
    async with AsyncSessionLocal() as session:
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


async def get_client_card_for_coach(
    *,
    telegram_id: int,
    client_id: str,
) -> ClientCard | None:
    async with AsyncSessionLocal() as session:
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
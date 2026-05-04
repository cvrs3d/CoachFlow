import asyncio
import sys
import uuid

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import Client, ClientCoachRelation, Coach, Consent, User


DEFAULT_POLICY_VERSION = "2026-05-03"


async def seed_client(
    *,
    coach_telegram_id: int,
    client_telegram_id: int,
    display_name: str,
    username: str | None = None,
) -> None:
    async with AsyncSessionLocal() as session:
        coach_result = await session.execute(
            select(Coach)
            .join(User, Coach.user_id == User.id)
            .where(User.telegram_id == coach_telegram_id)
            .where(User.role == "coach")
            .where(User.status == "active")
        )
        coach = coach_result.scalar_one_or_none()

        if coach is None:
            raise RuntimeError(
                f"Active coach with telegram_id={coach_telegram_id} not found"
            )

        user_result = await session.execute(
            select(User).where(User.telegram_id == client_telegram_id)
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            user = User(
                id=str(uuid.uuid4()),
                telegram_id=client_telegram_id,
                username=username,
                first_name=None,
                role="client",
                status="active",
            )
            session.add(user)
            await session.flush()
        else:
            user.username = username or user.username
            user.role = "client"
            user.status = "active"
            await session.flush()

        client_result = await session.execute(
            select(Client).where(Client.user_id == user.id)
        )
        client = client_result.scalar_one_or_none()

        if client is None:
            client = Client(
                id=str(uuid.uuid4()),
                user_id=user.id,
                display_name=display_name,
                status="active",
            )
            session.add(client)
            await session.flush()
        else:
            client.display_name = display_name
            client.status = "active"
            await session.flush()

        relation_result = await session.execute(
            select(ClientCoachRelation)
            .where(ClientCoachRelation.client_id == client.id)
            .where(ClientCoachRelation.coach_id == coach.id)
        )
        relation = relation_result.scalar_one_or_none()

        if relation is None:
            relation = ClientCoachRelation(
                id=str(uuid.uuid4()),
                client_id=client.id,
                coach_id=coach.id,
                status="active",
            )
            session.add(relation)
        else:
            relation.status = "active"

        consent_result = await session.execute(
            select(Consent)
            .where(Consent.user_id == user.id)
            .where(Consent.policy_version == DEFAULT_POLICY_VERSION)
        )
        consent = consent_result.scalar_one_or_none()

        if consent is None:
            session.add(
                Consent(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    policy_version=DEFAULT_POLICY_VERSION,
                )
            )

        await session.commit()

    print(
        "Client seeded:",
        f"coach_telegram_id={coach_telegram_id}",
        f"client_telegram_id={client_telegram_id}",
        f"display_name={display_name}",
    )


if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(
            "Usage: python -m app.seed_client "
            "<coach_telegram_id> <client_telegram_id> <display_name> [username]"
        )

    asyncio.run(
        seed_client(
            coach_telegram_id=int(sys.argv[1]),
            client_telegram_id=int(sys.argv[2]),
            display_name=sys.argv[3],
            username=sys.argv[4] if len(sys.argv) >= 5 else None,
        )
    )
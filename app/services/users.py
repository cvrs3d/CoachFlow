import uuid
from dataclasses import dataclass

from sqlalchemy import select

from app.db.database import AsyncSessionLocal, safe_commit
from app.db.models import Client, Coach, Consent, User


CURRENT_PRIVACY_POLICY_VERSION = "2026-05-03"


@dataclass
class CurrentUser:
    user: User
    coach: Coach | None = None
    client: Client | None = None


async def get_current_user_by_telegram_id(telegram_id: int) -> CurrentUser | None:
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            return None

        coach_result = await session.execute(
            select(Coach).where(Coach.user_id == user.id)
        )
        coach = coach_result.scalar_one_or_none()

        client_result = await session.execute(
            select(Client).where(Client.user_id == user.id)
        )
        client = client_result.scalar_one_or_none()

        return CurrentUser(user=user, coach=coach, client=client)


async def activate_user_after_consent(telegram_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            return False

        client_result = await session.execute(
            select(Client).where(Client.user_id == user.id)
        )
        client = client_result.scalar_one_or_none()

        if client is None:
            return False

        existing_consent_result = await session.execute(
            select(Consent)
            .where(Consent.user_id == user.id)
            .where(Consent.policy_version == CURRENT_PRIVACY_POLICY_VERSION)
        )
        existing_consent = existing_consent_result.scalar_one_or_none()

        if existing_consent is None:
            consent = Consent(
                id=str(uuid.uuid4()),
                user_id=user.id,
                policy_version=CURRENT_PRIVACY_POLICY_VERSION,
            )
            session.add(consent)

        user.status = "active"
        client.status = "active"

        await safe_commit(session)
        return True

async def set_client_display_name(
    telegram_id: int,
    display_name: str,
) -> bool:
    async with AsyncSessionLocal() as session:
        user_result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            return False

        client_result = await session.execute(
            select(Client).where(Client.user_id == user.id)
        )
        client = client_result.scalar_one_or_none()

        if client is None:
            return False

        client.display_name = display_name.strip()

        await safe_commit(session)
        return True
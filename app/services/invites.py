import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text

from app.db.database import AsyncSessionLocal, safe_commit
from app.db.models import (
    Client,
    ClientCoachRelation,
    Coach,
    InviteCode,
    User,
)

from app.db.database import safe_commit


def generate_invite_code() -> str:
    return secrets.token_urlsafe(12).replace("-", "_")[:16]


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


async def create_invite_for_coach(
    coach_id: str,
    max_uses: int = 1,
    expires_in_days: int = 7,
) -> InviteCode:
    async with AsyncSessionLocal() as session:
        # На случай редкого collision пробуем несколько раз
        for _ in range(5):
            code = generate_invite_code()

            existing = await session.execute(
                select(InviteCode).where(InviteCode.code == code)
            )
            if existing.scalar_one_or_none() is not None:
                continue

            invite = InviteCode(
                id=str(uuid.uuid4()),
                code=code,
                coach_id=coach_id,
                status="active",
                max_uses=max_uses,
                used_count=0,
                expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
            )

            session.add(invite)
            await safe_commit(session)
            await session.refresh(invite)
            return invite

        raise RuntimeError("Could not generate unique invite code")


async def create_invite_for_coach(
    coach_id: str,
    max_uses: int = 1,
    expires_in_days: int = 7,
) -> InviteCode:
    async with AsyncSessionLocal() as session:
        for _ in range(5):
            code = generate_invite_code()

            existing = await session.execute(
                select(InviteCode).where(InviteCode.code == code)
            )
            if existing.scalar_one_or_none() is not None:
                continue

            invite = InviteCode(
                id=str(uuid.uuid4()),
                code=code,
                coach_id=coach_id,
                status="active",
                max_uses=max_uses,
                used_count=0,
                expires_at=datetime.now(timezone.utc) + timedelta(days=expires_in_days),
            )

            session.add(invite)
            await safe_commit(session)
            await session.refresh(invite)
            return invite

        raise RuntimeError("Could not generate unique invite code")


@dataclass
class RedeemInviteResult:
    ok: bool
    reason: str | None = None
    user_id: str | None = None
    client_id: str | None = None
    coach_id: str | None = None


async def redeem_invite_code(
    *,
    code: str,
    telegram_id: int,
    username: str | None,
) -> RedeemInviteResult:
    """
    Активирует invite-ссылку и создает клиента.

    Важно:
    - invite используется атомарно через UPDATE ... WHERE ...
    - если код уже использован, UPDATE не вернет строку
    - клиент создается в той же транзакции
    """

    async with AsyncSessionLocal() as session:
        await session.execute(text("BEGIN IMMEDIATE"))

        try:
            # 1. Если пользователь уже активный клиент/тренер — не регистрируем повторно.
            existing_user_result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            existing_user = existing_user_result.scalar_one_or_none()

            if existing_user is not None:
                if existing_user.status == "active":
                    await session.rollback()
                    return RedeemInviteResult(
                        ok=False,
                        reason="already_registered",
                        user_id=existing_user.id,
                    )
                if existing_user.status == "pending":
                    await session.rollback()
                    return RedeemInviteResult(
                        ok=False,
                        reason="pending_consent",
                        user_id=existing_user.id,
                    )

            # 2. Атомарно занимаем invite.
            # SQLite поддерживает RETURNING для UPDATE.
            # Условие used_count < max_uses не даст использовать ссылку дважды.
            invite_result = await session.execute(
                text("""
                    UPDATE invite_codes
                    SET used_count = used_count + 1,
                        status = CASE
                            WHEN used_count + 1 >= max_uses THEN 'used'
                            ELSE status
                        END
                    WHERE code = :code
                      AND status = 'active'
                      AND used_count < max_uses
                      AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                    RETURNING id, coach_id
                """),
                {"code": code},
            )

            invite_row = invite_result.mappings().first()

            if invite_row is None:
                await session.rollback()
                return RedeemInviteResult(ok=False, reason="invalid_or_used_invite")

            invite_id = invite_row["id"]
            coach_id = invite_row["coach_id"]

            # 3. Создаем или обновляем user.
            if existing_user is None:
                user = User(
                    id=str(uuid.uuid4()),
                    telegram_id=telegram_id,
                    username=username,
                    role="client",
                    status="pending", 
                )
                session.add(user)
                await session.flush()
            else:
                user = existing_user
                user.username = username
                user.role = "client"
                user.status = "pending"
                await session.flush()

            # 4. Создаем client.
            client_result = await session.execute(
                select(Client).where(Client.user_id == user.id)
            )
            client = client_result.scalar_one_or_none()

            if client is None:
                client = Client(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    display_name=username,
                    status="pending",
                )
                session.add(client)
                await session.flush()
            else:
                client.status = "pending"
                await session.flush()

            # 5. Связываем client ↔ coach.
            relation_result = await session.execute(
                select(ClientCoachRelation)
                .where(ClientCoachRelation.client_id == client.id)
                .where(ClientCoachRelation.coach_id == coach_id)
            )
            relation = relation_result.scalar_one_or_none()

            if relation is None:
                relation = ClientCoachRelation(
                    id=str(uuid.uuid4()),
                    client_id=client.id,
                    coach_id=coach_id,
                    status="active",
                )
                session.add(relation)
            else:
                relation.status = "active"

            await safe_commit(session)

            return RedeemInviteResult(
                ok=True,
                user_id=user.id,
                client_id=client.id,
                coach_id=coach_id,
            )

        except Exception:
            await session.rollback()
            raise

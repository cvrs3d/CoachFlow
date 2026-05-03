import asyncio
import sys
import uuid

from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.models import User, Coach


async def seed_coach(
    telegram_id: int,
    username: str | None = None,
    timezone: str = "Europe/Prague"
) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                id=str(uuid.uuid4()),
                telegram_id=telegram_id,
                username=username,
                role="coach",
                status="active",
            )
            session.add(user)
            await session.flush()
        else:
            user.role = "coach"
            user.status = "active"

        result = await session.execute(
            select(Coach).where(Coach.user_id == user.id)
        )
        coach = result.scalar_one_or_none()

        if coach is None:
            coach = Coach(
                id=str(uuid.uuid4()),
                user_id=user.id,
                display_name=username or "Coach",
                timezone=timezone,
            )
            session.add(coach)
        else:
            coach.display_name = coach.display_name or "Coach"
            coach.timezone = timezone

        await session.commit()

    print(f"Coach seeded: telegram_id={telegram_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage: python -m app.seed_coach <telegram_id> [username]"
        )

    telegram_id_arg = int(sys.argv[1])
    username_arg = sys.argv[2] if len(sys.argv) >= 3 else None

    asyncio.run(
        seed_coach(
            telegram_id=telegram_id_arg,
            username=username_arg
        ))

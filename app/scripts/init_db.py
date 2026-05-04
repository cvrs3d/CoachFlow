import asyncio

from app.db.base import Base
from app.db.database import engine

# Важно: импорт моделей нужен, чтобы SQLAlchemy зарегистрировал таблицы в Base.metadata
from app.db import models  # noqa: F401


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_db())

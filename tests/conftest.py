from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models  # noqa: F401
from app.db.base import Base

TEST_DB_PATH = Path("tests/test.db")
TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"


@pytest.fixture(scope="session")
def test_db_path():
    return TEST_DB_PATH


@pytest.fixture(scope="session")
async def test_engine(test_db_path):
    if test_db_path.exists():
        test_db_path.unlink()

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"timeout": 5},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()

    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture
async def session_factory(test_engine):
    async_session_factory = async_sessionmaker(
        bind=test_engine,
        expire_on_commit=False,
    )

    yield async_session_factory

    # чистим данные после каждого теста
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

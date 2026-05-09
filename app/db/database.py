from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

import logging
from sqlalchemy.exc import IntegrityError, SQLAlchemyError


engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


logger = logging.getLogger(__name__)


async def safe_commit(session):
    try:
        await session.commit()

    except IntegrityError as e:
        await session.rollback()

        logger.warning(
            "Database integrity error: %s",
            str(e.orig) if hasattr(e, "orig") else str(e),
        )

        raise

    except SQLAlchemyError:
        await session.rollback()

        logger.exception("Database error during commit")

        raise
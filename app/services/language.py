from dataclasses import dataclass

from sqlalchemy import select

from app.bot.i18n import SUPPORTED_LANGUAGES
from app.db.database import AsyncSessionLocal
from app.db.models import User


@dataclass
class SetUserLanguageResult:
    ok: bool
    reason: str | None = None
    language_code: str | None = None
    role: str | None = None


async def set_user_language(
    *,
    telegram_id: int,
    language_code: str,
    session_factory=AsyncSessionLocal,
) -> SetUserLanguageResult:
    if language_code not in SUPPORTED_LANGUAGES:
        return SetUserLanguageResult(ok=False, reason="unsupported_language")

    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            return SetUserLanguageResult(ok=False, reason="user_not_found")

        user.language_code = language_code
        await session.commit()

        return SetUserLanguageResult(
            ok=True,
            language_code=language_code,
            role=user.role,
        )
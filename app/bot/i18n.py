from app.db.database import AsyncSessionLocal
from app.db.models import User
from sqlalchemy import select


SUPPORTED_LANGUAGES = {"ru", "en", "cs"}
DEFAULT_LANGUAGE = "ru"


TEXTS = {
    "ru": {
        "menu.overview": "📊 Обзор",
        "menu.create_invite": "🔗 Создать приглашение",
        "menu.schedule": "📅 Расписание",
        "menu.clients": "👥 Клиенты",
        "menu.meal_reports": "🍽 Отчеты еды",
        "menu.meal_schedule": "🍽 Расписание питания",
        "menu.choose_time": "📅 Выбрать время",
        "menu.my_bookings": "📋 Мои записи",
        "menu.send_meal_photo": "🍽 Отправить фото еды",
        "menu.my_meal_reports": "🍽 Мои отчеты еды",
        "menu.profile": "👤 Мой профиль",
        "menu.language": "🌐 Язык",
        "menu.placeholder": "Выберите действие",
        "language.choose": "Выберите язык интерфейса:",
        "language.updated": "Язык интерфейса обновлен.",
    },
    "en": {
        "menu.overview": "📊 Overview",
        "menu.create_invite": "🔗 Create invite",
        "menu.schedule": "📅 Schedule",
        "menu.clients": "👥 Clients",
        "menu.meal_reports": "🍽 Meal reports",
        "menu.meal_schedule": "🍽 Meal schedule",
        "menu.choose_time": "📅 Choose time",
        "menu.my_bookings": "📋 My bookings",
        "menu.send_meal_photo": "🍽 Send meal photo",
        "menu.my_meal_reports": "🍽 My meal reports",
        "menu.profile": "👤 My profile",
        "menu.language": "🌐 Language",
        "menu.placeholder": "Choose an action",
        "language.choose": "Choose interface language:",
        "language.updated": "Interface language updated.",
    },
    "cs": {
        "menu.overview": "📊 Přehled",
        "menu.create_invite": "🔗 Vytvořit pozvánku",
        "menu.schedule": "📅 Rozvrh",
        "menu.clients": "👥 Klienti",
        "menu.meal_reports": "🍽 Jídelní reporty",
        "menu.meal_schedule": "🍽 Jídelní plán",
        "menu.choose_time": "📅 Vybrat čas",
        "menu.my_bookings": "📋 Moje rezervace",
        "menu.send_meal_photo": "🍽 Poslat fotku jídla",
        "menu.my_meal_reports": "🍽 Moje jídelní reporty",
        "menu.profile": "👤 Můj profil",
        "menu.language": "🌐 Jazyk",
        "menu.placeholder": "Vyberte akci",
        "language.choose": "Vyberte jazyk rozhraní:",
        "language.updated": "Jazyk rozhraní byl změněn.",
    },
}


def t(key: str, language_code: str | None = None) -> str:
    language = language_code if language_code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    return TEXTS[language].get(key, TEXTS[DEFAULT_LANGUAGE].get(key, key))


async def get_user_language(
    telegram_id: int,
    session_factory=AsyncSessionLocal,
) -> str:
    async with session_factory() as session:
        result = await session.execute(
            select(User.language_code).where(User.telegram_id == telegram_id)
        )
        language_code = result.scalar_one_or_none()

    if language_code in SUPPORTED_LANGUAGES:
        return language_code

    return DEFAULT_LANGUAGE
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def ensure_utc(dt: datetime) -> datetime:
    """
    SQLite может вернуть naive datetime.
    В нашем проекте все naive datetime из БД считаем UTC.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def format_dt_for_timezone(
    dt: datetime,
    timezone_name: str = "Europe/Prague",
    fmt: str = "%d.%m.%Y %H:%M",
) -> str:
    utc_dt = ensure_utc(dt)
    local_dt = utc_dt.astimezone(ZoneInfo(timezone_name))
    return local_dt.strftime(fmt)


def format_slot_range_for_timezone(
    starts_at: datetime,
    ends_at: datetime,
    timezone_name: str = "Europe/Prague",
) -> str:
    start_text = format_dt_for_timezone(starts_at, timezone_name, "%d.%m.%Y %H:%M")
    end_text = format_dt_for_timezone(ends_at, timezone_name, "%H:%M")

    return f"{start_text}–{end_text}"
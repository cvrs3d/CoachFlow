from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import AvailabilitySlot
from app.bot.i18n import t
from app.utils.datetime import format_slot_range_for_timezone


def coach_schedule_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("schedule.add_slot", language_code),
                    callback_data="schedule:add_slot",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("schedule.my_slots", language_code),
                    callback_data="schedule:list_slots",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("schedule.download_calendar", language_code),
                    callback_data="schedule:ics",
                )
            ],
        ]
    )


def slot_duration_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t("schedule.duration_30", language_code), callback_data="slot_duration:30"),
                InlineKeyboardButton(text=t("schedule.duration_45", language_code), callback_data="slot_duration:45"),
            ],
            [
                InlineKeyboardButton(text=t("schedule.duration_60", language_code), callback_data="slot_duration:60"),
                InlineKeyboardButton(text=t("schedule.duration_90", language_code), callback_data="slot_duration:90"),
            ],
        ]
    )


def coach_slots_keyboard(
    slots: list[AvailabilitySlot],
    timezone_name: str = "Europe/Prague",
    language_code: str = "ru",
) -> InlineKeyboardMarkup:
    keyboard = []

    for slot in slots:
        slot_time = format_slot_range_for_timezone(
            slot.starts_at,
            slot.ends_at,
            timezone_name,
        )

        status_text = {
            "available": t("schedule.slot_status_available", language_code),
            "booked": t("schedule.slot_status_booked", language_code),
            "cancelled": t("schedule.slot_status_cancelled", language_code),
        }.get(slot.status, slot.status)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{slot_time} — {status_text}",
                    callback_data=f"schedule:open_slot:{slot.id}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def available_slot_management_keyboard(slot_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("schedule.delete_available_slot", "ru"),
                    callback_data=f"schedule:delete_available:{slot_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("common.back", "ru"),
                    callback_data="schedule:list_slots",
                )
            ],
        ]
    )


def booked_slot_management_keyboard(slot_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("schedule.cancel_booked_slot", "ru"),
                    callback_data=f"sc:cb:{slot_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("schedule.add_to_calendar", "ru"),
                    callback_data=f"sc:ics:{slot_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("common.back", "ru"),
                    callback_data="schedule:list_slots",
                )
            ],
        ]
    )


def confirm_cancel_booked_slot_keyboard(slot_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("schedule.confirm_cancel", "ru"),
                    callback_data=f"sc:ccb:{slot_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("common.back", "ru"),
                    callback_data=f"schedule:open_slot:{slot_id}",
                )
            ],
        ]
    )


def slot_date_keyboard(
    timezone_name: str = "Europe/Prague",
    days_count: int = 4,
    language_code: str = "ru",
) -> InlineKeyboardMarkup:
    today = datetime.now(ZoneInfo(timezone_name)).date()

    labels = [
        t("schedule.today", language_code),
        t("schedule.tomorrow", language_code),
        t("schedule.day_after_tomorrow", language_code),
        t("schedule.in_days", language_code, days=3),
    ]

    keyboard = []

    for offset in range(days_count):
        target_date = today + timedelta(days=offset)
        label = labels[offset] if offset < len(labels) else t("schedule.in_days", language_code, days=offset)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{label} · {target_date.strftime('%d.%m')}",
                    callback_data=f"sd:{target_date.isoformat()}",  # sd = schedule date
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                    text=t("schedule.enter_date_manually", language_code),
                callback_data="sd:manual",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def slot_time_keyboard(
    start_hour: int = 10,
    end_hour: int = 18,
    language_code: str = "ru",
) -> InlineKeyboardMarkup:
    keyboard = []

    row = []

    for hour in range(start_hour, end_hour + 1):
        time_text = f"{hour:02d}:00"

        row.append(
            InlineKeyboardButton(
                text=time_text,
                callback_data=f"st:{time_text}",  # st = schedule time.
            )
        )

        if len(row) == 3:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    keyboard.append(
        [
            InlineKeyboardButton(
                text=t("schedule.enter_time_manually", language_code),
                callback_data="st:manual",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

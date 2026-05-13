from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import AvailabilitySlot
from app.utils.datetime import format_slot_range_for_timezone


def coach_schedule_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить слот",
                    callback_data="schedule:add_slot",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 Мои слоты",
                    callback_data="schedule:list_slots",
                )
            ],
        ]
    )


def slot_duration_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="30 мин", callback_data="slot_duration:30"),
                InlineKeyboardButton(text="45 мин", callback_data="slot_duration:45"),
            ],
            [
                InlineKeyboardButton(text="60 мин", callback_data="slot_duration:60"),
                InlineKeyboardButton(text="90 мин", callback_data="slot_duration:90"),
            ],
        ]
    )


def coach_slots_keyboard(
    slots: list[AvailabilitySlot],
    timezone_name: str = "Europe/Prague",
) -> InlineKeyboardMarkup:
    keyboard = []

    for slot in slots:
        slot_time = format_slot_range_for_timezone(
            slot.starts_at,
            slot.ends_at,
            timezone_name,
        )

        status_text = {
            "available": "свободен",
            "booked": "занят",
            "cancelled": "отменен",
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
                    text="🗑 Удалить свободный слот",
                    callback_data=f"schedule:delete_available:{slot_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к слотам",
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
                    text="❌ Отменить занятие и уведомить клиента",
                    callback_data=f"sc:cb:{slot_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к слотам",
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
                    text="✅ Да, отменить",
                    callback_data=f"sc:ccb:{slot_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"schedule:open_slot:{slot_id}",
                )
            ],
        ]
    )


def slot_date_keyboard(
    timezone_name: str = "Europe/Prague",
    days_count: int = 4,
) -> InlineKeyboardMarkup:
    today = datetime.now(ZoneInfo(timezone_name)).date()

    labels = [
        "Сегодня",
        "Завтра",
        "Послезавтра",
        "+3 дня",
    ]

    keyboard = []

    for offset in range(days_count):
        target_date = today + timedelta(days=offset)
        label = labels[offset] if offset < len(labels) else f"+{offset} дней"

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
                text="✍️ Ввести дату вручную",
                callback_data="sd:manual",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def slot_time_keyboard(
    start_hour: int = 10,
    end_hour: int = 18,
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
                text="✍️ Ввести время вручную",
                callback_data="st:manual",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from datetime import timedelta

from app.db.models import AvailabilitySlot


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
                    callback_data=f"schedule:cancel_booked:{slot_id}",
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
                    callback_data=f"schedule:confirm_cancel_booked:{slot_id}",
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
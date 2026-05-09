from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def meal_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Завтрак",
                    callback_data="mr:t:breakfast",
                ),
                InlineKeyboardButton(
                    text="Обед",
                    callback_data="mr:t:lunch",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Ужин",
                    callback_data="mr:t:dinner",
                ),
                InlineKeyboardButton(
                    text="Перекус",
                    callback_data="mr:t:snack",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Другое",
                    callback_data="mr:t:other",
                ),
            ],
        ]
    )

from datetime import datetime

from app.db.models import Client, MealReport


MEAL_TYPE_LABELS = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "dinner": "Ужин",
    "snack": "Перекус",
    "other": "Другое",
}

#mr:o:<uuid>   open report
# mr:ok:<uuid>  verdict ok
# mr:ni:<uuid>  needs improvement
# mr:q:<uuid>   question


def pending_meal_reports_keyboard(
    items: list[tuple[MealReport, Client]],
) -> InlineKeyboardMarkup:
    keyboard = []

    for report, client in items:
        client_name = client.display_name or "Без имени"
        meal_type = MEAL_TYPE_LABELS.get(report.meal_type, report.meal_type)

        submitted_at = report.submitted_at
        if isinstance(submitted_at, datetime):
            submitted_text = submitted_at.strftime("%d.%m %H:%M")
        else:
            submitted_text = str(submitted_at)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{client_name} · {meal_type} · {submitted_text}",
                    callback_data=f"mr:o:{report.id}",
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def meal_review_keyboard(report_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Хорошо",
                    callback_data=f"mr:ok:{report_id}",
                ),
                InlineKeyboardButton(
                    text="⚠️ Улучшить",
                    callback_data=f"mr:ni:{report_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❓ Уточнить",
                    callback_data=f"mr:q:{report_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К отчетам",
                    callback_data="mr:list",
                ),
            ],
        ]
    )
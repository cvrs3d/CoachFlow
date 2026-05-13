from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.db.models import Client, MealReport


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


MEAL_TYPE_LABELS = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "dinner": "Ужин",
    "snack": "Перекус",
    "other": "Другое",
}

# mr:o:<uuid>   open report
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

        status_text = {
            "submitted": "на проверке",
            "in_review": "на проверке",
            "needs_clarification": "нужно уточнение",
            "reviewed": "проверен",
        }.get(report.status, report.status)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{client_name} · {meal_type} · {submitted_text} · {status_text}",
                    callback_data=f"mr:o:{report.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ К фильтрам",
                callback_data="mr:filters",
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


# mr:co:<report_id> = meal report client open
# mr:clist = client reports list


def client_meal_reports_keyboard(
    reports: list[MealReport],
) -> InlineKeyboardMarkup:
    keyboard = []

    for report in reports:
        meal_type = MEAL_TYPE_LABELS.get(report.meal_type, report.meal_type)

        submitted_at = report.submitted_at
        if isinstance(submitted_at, datetime):
            submitted_text = submitted_at.strftime("%d.%m %H:%M")
        else:
            submitted_text = str(submitted_at)

        status_text = {
            "submitted": "на проверке",
            "in_review": "на проверке",
            "reviewed": "проверен",
            "needs_clarification": "нужно уточнение",
            "archived": "архив",
            "draft": "черновик",
        }.get(report.status, report.status)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{meal_type} · {submitted_text} · {status_text}",
                    callback_data=f"mr:co:{report.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ К фильтрам",
                callback_data="mr:cfilters",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def client_meal_report_card_keyboard(
    report_id: str | None = None,
    can_reply: bool = False,
) -> InlineKeyboardMarkup:
    keyboard = []

    if can_reply and report_id is not None:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="✍️ Ответить тренеру",
                    callback_data=f"mr:reply:{report_id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ К моим отчетам",
                callback_data="mr:cfilters",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def coach_meal_reports_filter_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟡 На проверку",
                    callback_data="mr:f:pending",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❓ Нужно уточнение",
                    callback_data="mr:f:clarification",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Проверенные",
                    callback_data="mr:f:reviewed",
                )
            ],
        ]
    )


def coach_client_meal_reports_keyboard(
    items: list[tuple[MealReport, Client]],
    client_id: str,
) -> InlineKeyboardMarkup:
    keyboard = []

    for report, client in items:
        meal_type = MEAL_TYPE_LABELS.get(report.meal_type, report.meal_type)

        submitted_at = report.submitted_at
        if isinstance(submitted_at, datetime):
            submitted_text = submitted_at.strftime("%d.%m %H:%M")
        else:
            submitted_text = str(submitted_at)

        status_text = {
            "draft": "черновик",
            "submitted": "на проверке",
            "in_review": "на проверке",
            "reviewed": "проверен",
            "needs_clarification": "нужно уточнение",
            "archived": "архив",
        }.get(report.status, report.status)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{meal_type} · {submitted_text} · {status_text}",
                    callback_data=f"mr:o:{report.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="⬅️ К карточке клиента",
                callback_data=f"client:open:{client_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def client_meal_reports_filter_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 Все",
                    callback_data="mr:cf:all",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🟡 На проверке",
                    callback_data="mr:cf:pending",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Проверенные",
                    callback_data="mr:cf:reviewed",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❓ Нужно уточнение",
                    callback_data="mr:cf:clarification",
                )
            ],
        ]
    )

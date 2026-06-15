from datetime import datetime

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks.meal_reports import (
    ClientMealReportFilterCallback,
    CoachMealReportFilterCallback,
    MealTypeCallback,
    OpenClientMealReportCallback,
    OpenCoachMealReportCallback,
    ReplyMealReportCallback,
    ReviewMealReportCallback,
)
from app.bot.handlers.meal_report_labels import (
    get_client_report_filter_label,
    get_coach_report_filter_label,
    get_meal_type_label,
    get_report_status_label,
    get_verdict_label,
)
from app.bot.i18n import t
from app.db.models import Client, MealReport


def meal_type_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("meal_type.breakfast", language_code),
                    callback_data=MealTypeCallback(meal_type="breakfast").pack(),
                ),
                InlineKeyboardButton(
                    text=t("meal_type.lunch", language_code),
                    callback_data=MealTypeCallback(meal_type="lunch").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("meal_type.dinner", language_code),
                    callback_data=MealTypeCallback(meal_type="dinner").pack(),
                ),
                InlineKeyboardButton(
                    text=t("meal_type.snack", language_code),
                    callback_data=MealTypeCallback(meal_type="snack").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("meal_type.other", language_code),
                    callback_data=MealTypeCallback(meal_type="other").pack(),
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
    language_code: str = "ru",
) -> InlineKeyboardMarkup:
    keyboard = []

    for report, client in items:
        client_name = client.display_name or t("clients.without_name", language_code)
        meal_type = get_meal_type_label(report.meal_type, language_code)

        submitted_at = report.submitted_at
        if isinstance(submitted_at, datetime):
            submitted_text = submitted_at.strftime("%d.%m %H:%M")
        else:
            submitted_text = str(submitted_at)

        status_text = get_report_status_label(report.status, language_code)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{client_name} · {meal_type} · {submitted_text} · {status_text}",
                    callback_data=OpenCoachMealReportCallback(report_id=report.id).pack(),
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=t("meal_reports.back_to_filters", language_code),
                callback_data="mr:filters",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def meal_review_keyboard(report_id: str, language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("meal_reports.review_ok", language_code),
                    callback_data=ReviewMealReportCallback(
                        action="ok",
                        report_id=report_id,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text=t("meal_reports.review_needs_improvement", language_code),
                    callback_data=ReviewMealReportCallback(
                        action="needs_improvement",
                        report_id=report_id,
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("meal_reports.review_question", language_code),
                    callback_data=ReviewMealReportCallback(
                        action="question",
                        report_id=report_id,
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=t("meal_reports.back_to_reports", language_code),
                    callback_data="mr:list",
                ),
            ],
        ]
    )


# mr:co:<report_id> = meal report client open
# mr:clist = client reports list


def client_meal_reports_keyboard(
    reports: list[MealReport],
    language_code: str = "ru",
) -> InlineKeyboardMarkup:
    keyboard = []

    for report in reports:
        meal_type = get_meal_type_label(report.meal_type, language_code)

        submitted_at = report.submitted_at
        if isinstance(submitted_at, datetime):
            submitted_text = submitted_at.strftime("%d.%m %H:%M")
        else:
            submitted_text = str(submitted_at)

        status_text = get_report_status_label(report.status, language_code)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{meal_type} · {submitted_text} · {status_text}",
                    callback_data=OpenClientMealReportCallback(report_id=report.id).pack(),
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text=t("meal_reports.back_to_filters", language_code),
                callback_data="mr:cfilters",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def client_meal_report_card_keyboard(
    report_id: str | None = None,
    can_reply: bool = False,
    language_code: str = "ru",
) -> InlineKeyboardMarkup:
    keyboard = []

    if can_reply and report_id is not None:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=t("meal_reports.reply_to_coach", language_code),
                    callback_data=ReplyMealReportCallback(report_id=report_id).pack(),
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                    text=t("meal_reports.back_to_my_reports", language_code),
                callback_data="mr:cfilters",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def coach_meal_reports_filter_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("coach_report_filter.pending", language_code),
                    callback_data=CoachMealReportFilterCallback(report_filter="pending").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("coach_report_filter.clarification", language_code),
                    callback_data=CoachMealReportFilterCallback(
                        report_filter="clarification"
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("coach_report_filter.reviewed", language_code),
                    callback_data=CoachMealReportFilterCallback(report_filter="reviewed").pack(),
                )
            ],
        ]
    )


def coach_client_meal_reports_keyboard(
    items: list[tuple[MealReport, Client]],
    client_id: str,
    language_code: str = "ru",
) -> InlineKeyboardMarkup:
    keyboard = []

    for report, _client in items:
        meal_type = get_meal_type_label(report.meal_type, language_code)

        submitted_at = report.submitted_at
        if isinstance(submitted_at, datetime):
            submitted_text = submitted_at.strftime("%d.%m %H:%M")
        else:
            submitted_text = str(submitted_at)

        status_text = get_report_status_label(report.status, language_code)

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
                text=t("clients.back_to_card", language_code),
                callback_data=f"client:open:{client_id}",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def client_meal_reports_filter_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("client_report_filter.all", language_code),
                    callback_data=ClientMealReportFilterCallback(report_filter="all").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("client_report_filter.pending", language_code),
                    callback_data=ClientMealReportFilterCallback(report_filter="pending").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("client_report_filter.reviewed", language_code),
                    callback_data=ClientMealReportFilterCallback(report_filter="reviewed").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("client_report_filter.clarification", language_code),
                    callback_data=ClientMealReportFilterCallback(
                        report_filter="clarification"
                    ).pack(),
                )
            ],
        ]
    )

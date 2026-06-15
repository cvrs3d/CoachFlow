from app.bot.handlers.meal_report_labels import (
    get_meal_type_label,
    get_report_status_label,
    get_verdict_label,
)
from app.bot.i18n import t


def format_coach_meal_report_caption(card, language_code: str = "ru") -> str:
    client_name = card.client.display_name or t("clients.without_name", language_code)
    meal_type_label = get_meal_type_label(card.report.meal_type, language_code)
    status_label = get_report_status_label(card.report.status, language_code)

    caption = (
        f"{t('meal_reports.title_coach', language_code)}\n\n"
        f"{t('clients.client_label', language_code, client_name=client_name)}\n"
        f"{t('meal_reports.meal_type_label', language_code, meal_type_label=meal_type_label)}\n"
        f"{t('meal_reports.status_label', language_code, status_label=status_label)}"
    )

    if card.report.client_comment:
        caption += (
            f"\n\n{t('meal_reports.client_comment_label', language_code)}\n"
            f"{card.report.client_comment}"
        )

    return caption


def format_client_meal_report_caption(card, language_code: str = "ru") -> str:
    meal_type_label = get_meal_type_label(card.report.meal_type, language_code)
    status_label = get_report_status_label(card.report.status, language_code)

    caption = (
        f"{t('meal_reports.title_client', language_code)}\n\n"
        f"{t('meal_reports.meal_type_label', language_code, meal_type_label=meal_type_label)}\n"
        f"{t('meal_reports.status_label', language_code, status_label=status_label)}"
    )

    if card.report.client_comment:
        caption += (
            f"\n\n{t('meal_reports.your_comment_label', language_code)}\n"
            f"{card.report.client_comment}"
        )

    if card.review is not None:
        verdict_label = get_verdict_label(card.review.verdict, language_code)

        caption += (
            f"\n\n{t('meal_reports.coach_review_label', language_code)}\n"
            f"{t('meal_reports.result_label', language_code, verdict_label=verdict_label)}"
        )

        if card.review.comment:
            caption += (
                f"\n{t('meal_reports.coach_comment_label', language_code)}\n"
                f"{card.review.comment}"
            )

    if card.report.clarification_response:
        caption += (
            f"\n\n{t('meal_reports.your_reply_label', language_code)}\n"
            f"{card.report.clarification_response}"
        )

    return caption

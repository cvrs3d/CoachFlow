from app.bot.handlers.meal_report_labels import (
    MEAL_TYPE_LABELS,
    REPORT_STATUS_LABELS,
    VERDICT_LABELS,
)


def format_coach_meal_report_caption(card) -> str:
    client_name = card.client.display_name or "без имени"

    meal_type_label = MEAL_TYPE_LABELS.get(
        card.report.meal_type,
        card.report.meal_type,
    )

    caption = (
        f"Отчет еды\n\n"
        f"Клиент: {client_name}\n"
        f"Прием пищи: {meal_type_label}\n"
        f"Статус: {card.report.status}"
    )

    if card.report.client_comment:
        caption += f"\n\nКомментарий клиента:\n{card.report.client_comment}"

    return caption


def format_client_meal_report_caption(card) -> str:
    meal_type_label = MEAL_TYPE_LABELS.get(
        card.report.meal_type,
        card.report.meal_type,
    )

    status_label = REPORT_STATUS_LABELS.get(
        card.report.status,
        card.report.status,
    )

    caption = f"Ваш отчет еды\n\nПрием пищи: {meal_type_label}\nСтатус: {status_label}"

    if card.report.client_comment:
        caption += f"\n\nВаш комментарий:\n{card.report.client_comment}"

    if card.review is not None:
        verdict_label = VERDICT_LABELS.get(card.review.verdict, card.review.verdict)

        caption += f"\n\nПроверка тренера:\nРезультат: {verdict_label}"

        if card.review.comment:
            caption += f"\nКомментарий:\n{card.review.comment}"

    if card.report.clarification_response:
        caption += f"\n\nВаш ответ тренеру:\n{card.report.clarification_response}"

    return caption

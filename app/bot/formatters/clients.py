from app.utils.datetime import format_slot_range_for_timezone

APPOINTMENT_STATUS_LABELS = {
    "booked": "запланирована",
    "cancelled_by_client": "отменена клиентом",
    "cancelled_by_coach": "отменена тренером",
    "completed": "завершена",
    "no_show": "не пришел",
}

def format_client_appointments_text(result) -> str:
    assert result.client is not None

    client_name = result.client.display_name or "без имени"
    timezone_name = result.coach_timezone or "Europe/Prague"

    lines = [
        f"📅 Записи клиента: {client_name}",
        "",
        "Будущие записи:",
    ]

    future_items = result.future_items or []
    history_items = result.history_items or []

    if not future_items:
        lines.append("- нет будущих записей")
    else:
        for item in future_items:
            slot_time = format_slot_range_for_timezone(
                item.slot.starts_at,
                item.slot.ends_at,
                timezone_name,
            )
            status = APPOINTMENT_STATUS_LABELS.get(
                item.appointment.status,
                item.appointment.status,
            )
            lines.append(f"- {slot_time} · {status}")

    lines.extend(
        [
            "",
            "История:",
        ]
    )

    if not history_items:
        lines.append("- истории пока нет")
    else:
        for item in history_items:
            slot_time = format_slot_range_for_timezone(
                item.slot.starts_at,
                item.slot.ends_at,
                timezone_name,
            )
            status = APPOINTMENT_STATUS_LABELS.get(
                item.appointment.status,
                item.appointment.status,
            )
            lines.append(f"- {slot_time} · {status}")

    return "\n".join(lines)

def format_client_card_text(result) -> str:
    assert result.card is not None

    card = result.card
    client = card.client
    user = card.user
    stats = card.stats

    client_name = client.display_name or "без имени"
    username = f"@{user.username}" if user.username else "не указан"

    if card.upcoming_appointment is None:
        upcoming_text = "нет будущих записей"
    else:
        upcoming_text = format_slot_range_for_timezone(
            card.upcoming_appointment.starts_at,
            card.upcoming_appointment.ends_at,
            result.coach_timezone or "Europe/Prague",
        )

    return (
        f"👤 Клиент: {client_name}\n\n"
        f"Telegram username: {username}\n"
        f"Статус: {client.status}\n\n"
        f"Ближайшая запись:\n"
        f"{upcoming_text}\n\n"
        f"Food reports за 7 дней:\n"
        f"- отправлено: {stats.reports_7d_count}\n"
        f"- проверено: {stats.reviewed_7d_count}\n"
        f"- требует улучшения: {stats.needs_improvement_7d_count}\n"
        f"- ждет ответа клиента: {stats.waiting_clarification_count}"
    )
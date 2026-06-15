from app.bot.i18n import t
from app.utils.datetime import format_slot_range_for_timezone


def get_appointment_status_label(status: str, language_code: str) -> str:
    return t(f"appointment_status.{status}", language_code)


def get_client_status_label(status: str, language_code: str) -> str:
    key = f"client_status.{status}"
    return t(key, language_code) if key in {f"client_status.{name}" for name in ("active", "inactive", "pending", "unknown")} else t("client_status.unknown", language_code)


def format_client_appointments_text(result, language_code: str = "ru") -> str:
    assert result.client is not None

    client_name = result.client.display_name or t("clients.without_name", language_code)
    timezone_name = result.coach_timezone or "Europe/Prague"

    lines = [
        t("clients.appointments_title", language_code, client_name=client_name),
        "",
        t("clients.future_appointments_title", language_code),
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
            status = get_appointment_status_label(item.appointment.status, language_code)
            lines.append(f"- {slot_time} · {status}")

    lines.extend(
        [
            "",
            t("clients.history_title", language_code),
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
            status = get_appointment_status_label(item.appointment.status, language_code)
            lines.append(f"- {slot_time} · {status}")

    return "\n".join(lines)


def format_client_card_text(result, language_code: str = "ru") -> str:
    assert result.card is not None

    card = result.card
    client = card.client
    user = card.user
    stats = card.stats

    client_name = client.display_name or t("clients.without_name", language_code)
    username = f"@{user.username}" if user.username else t("clients.username_unknown", language_code)
    status_label = get_client_status_label(client.status, language_code)

    if card.upcoming_appointment is None:
        upcoming_text = t("clients.no_future_appointments", language_code)
    else:
        upcoming_text = format_slot_range_for_timezone(
            card.upcoming_appointment.starts_at,
            card.upcoming_appointment.ends_at,
            result.coach_timezone or "Europe/Prague",
        )

    return (
        f"{t('clients.card_title', language_code, client_name=client_name)}\n\n"
        f"{t('clients.telegram_username', language_code, username=username)}\n"
        f"{t('clients.status_label', language_code, status=status_label)}\n\n"
        f"{t('clients.upcoming_appointment_label', language_code)}\n"
        f"{upcoming_text}\n\n"
        f"{t('clients.reports_7d_title', language_code)}\n"
        f"- {t('clients.sent_count', language_code, count=stats.reports_7d_count)}\n"
        f"- {t('clients.reviewed_count', language_code, count=stats.reviewed_7d_count)}\n"
        f"- {t('clients.needs_improvement_count', language_code, count=stats.needs_improvement_7d_count)}\n"
        f"- {t('clients.waiting_clarification_count', language_code, count=stats.waiting_clarification_count)}"
    )

MEAL_TYPE_LABELS = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "dinner": "Ужин",
    "snack": "Перекус",
    "other": "Другое",
}


def format_meal_checkin_schedules_text(result) -> str:
    timezone_name = result.timezone_name or "Europe/Prague"
    schedules = result.schedules or []

    lines = [
        "🍽 Расписание питания",
        "",
        f"Часовой пояс: {timezone_name}",
        "",
    ]

    if not schedules:
        lines.extend(
            [
                "Активное расписание пока не настроено.",
                "",
                "Можно создать дефолтное расписание:",
                "- Завтрак 09:00",
                "- Обед 13:00",
                "- Ужин 19:00",
            ]
        )
        return "\n".join(lines)

    lines.append("Активные напоминания:")

    for schedule in schedules:
        meal_type = MEAL_TYPE_LABELS.get(schedule.meal_type, schedule.meal_type)
        lines.append(f"- {meal_type}: {schedule.local_time}")

    return "\n".join(lines)
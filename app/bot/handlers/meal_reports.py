from aiogram import Router

from app.bot.handlers import (
    meal_report_submission,
    coach_meal_reports,
    client_meal_reports,
)

router = Router()

router.include_router(meal_report_submission.router)
router.include_router(coach_meal_reports.router)
router.include_router(client_meal_reports.router)

COACH_REPORT_FILTER_LABELS = {
    "pending": "Отчеты на проверку",
    "clarification": "Отчеты, ожидающие уточнения клиента",
    "reviewed": "Проверенные отчеты",
}

MEAL_TYPE_LABELS = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "dinner": "Ужин",
    "snack": "Перекус",
    "other": "Другое",
}

CLIENT_REPORT_FILTER_LABELS = {
    "all": "Все отчеты еды",
    "pending": "Отчеты на проверке",
    "reviewed": "Проверенные отчеты",
    "clarification": "Отчеты, где нужно уточнение",
}

VERDICT_LABELS = {
    "ok": "Хорошо ✅",
    "needs_improvement": "Нужно улучшить ⚠️",
    "question": "Нужно уточнение ❓",
}

REPORT_STATUS_LABELS = {
    "draft": "Черновик",
    "submitted": "На проверке",
    "in_review": "На проверке",
    "reviewed": "Проверен",
    "needs_clarification": "Нужно уточнение",
    "archived": "Архив",
}


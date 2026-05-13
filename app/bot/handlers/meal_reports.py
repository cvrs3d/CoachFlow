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


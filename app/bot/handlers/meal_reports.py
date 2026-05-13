from aiogram import Router

from app.bot.handlers import (
    client_meal_reports,
    coach_meal_reports,
    meal_report_submission,
)

router = Router()

router.include_router(meal_report_submission.router)
router.include_router(coach_meal_reports.router)
router.include_router(client_meal_reports.router)

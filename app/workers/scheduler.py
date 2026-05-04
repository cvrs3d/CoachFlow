from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services.reminders import send_appointment_24h_reminders


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        send_appointment_24h_reminders,
        trigger="interval",
        minutes=15,
        kwargs={"bot": bot},
        id="send_appointment_24h_reminders",
        replace_existing=True,
    )

    scheduler.start()

    return scheduler
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks.common import CommonCallback
from app.bot.i18n import t


def cancel_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("common.cancel", language_code),
                    callback_data=CommonCallback(action="cancel").pack(),
                )
            ]
        ]
    )
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def privacy_consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Согласен",
                    callback_data="privacy:accept",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Не согласен",
                    callback_data="privacy:decline",
                )
            ],
        ]
    )
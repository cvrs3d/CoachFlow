from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.i18n import t


def privacy_consent_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("privacy.agree", language_code),
                    callback_data="privacy:accept",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("privacy.disagree", language_code),
                    callback_data="privacy:decline",
                )
            ],
        ]
    )

def delete_my_data_confirm_keyboard(language_code: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t("privacy.delete_confirm", language_code),
                    callback_data="privacy:delete_confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t("common.cancel", language_code),
                    callback_data="privacy:delete_cancel",
                )
            ],
        ]
    )
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

def delete_my_data_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить запрос удаления",
                    callback_data="privacy:delete_confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="privacy:delete_cancel",
                )
            ],
        ]
    )
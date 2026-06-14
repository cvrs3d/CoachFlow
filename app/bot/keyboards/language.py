from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:set:ru"),
            ],
            [
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:set:en"),
            ],
            [
                InlineKeyboardButton(text="🇨🇿 Čeština", callback_data="lang:set:cs"),
            ],
        ]
    )
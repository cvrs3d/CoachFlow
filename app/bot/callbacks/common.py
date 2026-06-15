from aiogram.filters.callback_data import CallbackData


class CommonCallback(CallbackData, prefix="common"):
    action: str
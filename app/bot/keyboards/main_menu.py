from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def coach_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📊 Обзор"),
            ],
            [
                KeyboardButton(text="🔗 Создать приглашение"),
            ],
            [
                KeyboardButton(text="📅 Расписание"),
                KeyboardButton(text="👥 Клиенты"),
            ],
            [
                KeyboardButton(text="🍽 Отчеты еды"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def client_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📅 Выбрать время"),
                KeyboardButton(text="📋 Мои записи"),
            ],
            [
                KeyboardButton(text="🍽 Отправить фото еды"),
                KeyboardButton(text="🍽 Мои отчеты еды"),
            ],
            [
                KeyboardButton(text="👤 Мой профиль"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )
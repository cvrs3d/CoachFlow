from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message


def _is_message_not_modified(error: TelegramBadRequest) -> bool:
    return "message is not modified" in str(error).lower()


def _has_no_text_to_edit(error: TelegramBadRequest) -> bool:
    return "there is no text in the message to edit" in str(error).lower()


def _has_no_caption_to_edit(error: TelegramBadRequest) -> bool:
    return "there is no caption in the message to edit" in str(error).lower()


async def safe_edit_text(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """
    Пытается редактировать text-сообщение.

    Возвращает:
    - True, если edit прошел
    - False, если Telegram отказал по ожидаемой причине

    Не кидает ошибку на:
    - message is not modified
    - there is no text in the message to edit
    """

    try:
        await message.edit_text(
            text=text,
            reply_markup=reply_markup,
        )
        return True

    except TelegramBadRequest as error:
        if _is_message_not_modified(error):
            return False

        if _has_no_text_to_edit(error):
            return False

        raise


async def safe_edit_caption(
    message: Message,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """
    Пытается редактировать caption у media-сообщения.
    """

    try:
        await message.edit_caption(
            caption=caption,
            reply_markup=reply_markup,
        )
        return True

    except TelegramBadRequest as error:
        if _is_message_not_modified(error):
            return False

        if _has_no_caption_to_edit(error):
            return False

        raise


async def safe_edit_reply_markup(
    message: Message,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> bool:
    """
    Безопасно редактирует только inline-клавиатуру.
    Подходит и для text messages, и для photo/media messages.
    """

    try:
        await message.edit_reply_markup(reply_markup=reply_markup)
        return True

    except TelegramBadRequest as error:
        if _is_message_not_modified(error):
            return False

        raise


async def safe_answer_or_edit_text(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """
    Если сообщение текстовое — пытается edit_text.
    Если edit_text невозможен — отправляет новое сообщение.
    """

    edited = await safe_edit_text(
        message=message,
        text=text,
        reply_markup=reply_markup,
    )

    if edited:
        return

    await message.answer(
        text=text,
        reply_markup=reply_markup,
    )
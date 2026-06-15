from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.meal_reports import (
    ClientMealReportFilterCallback,
    OpenClientMealReportCallback,
    ReplyMealReportCallback,
)
from app.bot.callbacks.menu import MainMenuCallback
from app.bot.i18n import get_user_language, t
from app.bot.formatters.meal_reports import format_client_meal_report_caption
from app.bot.handlers.meal_report_labels import (
    CLIENT_REPORT_FILTER_LABELS,
)
from app.bot.keyboards.common import cancel_keyboard
from app.bot.keyboards.meal_reports import (
    client_meal_report_card_keyboard,
    client_meal_reports_filter_keyboard,
    client_meal_reports_keyboard,
)
from app.bot.states.meal_reports import MealReportStates
from app.bot.utils.safe_messages import (
    safe_answer_or_edit_text,
    safe_edit_reply_markup,
    safe_edit_text,
)
from app.services.meal_reports import (
    get_meal_report_for_client,
    list_meal_reports_for_client_by_filter,
    respond_to_meal_report_clarification,
)
from app.services.notifications import send_logged_message

router = Router()

@router.callback_query(MainMenuCallback.filter(F.action == "client_meal_reports"))
async def my_meal_reports_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    await callback.message.answer(
        "Выберите раздел отчетов еды:",
        reply_markup=client_meal_reports_filter_keyboard(),
    )

@router.callback_query(F.data == "mr:cfilters")
async def client_meal_reports_filters_callback_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    await safe_edit_reply_markup(callback.message, reply_markup=None)

    await callback.message.answer(
        "Выберите раздел отчетов еды:",
        reply_markup=client_meal_reports_filter_keyboard(),
    )


@router.callback_query(ClientMealReportFilterCallback.filter())
async def client_meal_reports_by_filter_handler(
    callback: CallbackQuery,
    callback_data: ClientMealReportFilterCallback,
) -> None:
    report_filter = callback_data.report_filter

    reports = await list_meal_reports_for_client_by_filter(
        telegram_id=callback.from_user.id,
        report_filter=report_filter,
        limit=10,
    )

    await callback.answer()

    title = CLIENT_REPORT_FILTER_LABELS.get(report_filter, "Отчеты еды")

    if not reports:
        await safe_answer_or_edit_text(
            callback.message,
            f"{title}.\n\nСписок пуст.",
            reply_markup=client_meal_reports_filter_keyboard(),
        )
        return

    await safe_answer_or_edit_text(
        callback.message,
        f"{title}:",
        reply_markup=client_meal_reports_keyboard(reports),
    )


@router.callback_query(F.data == "mr:clist")
async def my_meal_reports_callback_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    await safe_edit_reply_markup(callback.message, reply_markup=None)

    await callback.message.answer(
        "Выберите раздел отчетов еды:",
        reply_markup=client_meal_reports_filter_keyboard(),
    )


@router.callback_query(OpenClientMealReportCallback.filter())
async def open_client_meal_report_handler(
    callback: CallbackQuery,
    callback_data: OpenClientMealReportCallback,
) -> None:
    report_id = callback_data.report_id

    card = await get_meal_report_for_client(
        telegram_id=callback.from_user.id,
        report_id=report_id,
    )

    await callback.answer()

    if card is None:
        await safe_edit_text(callback.message, text="Отчет не найден или у вас нет доступа.")
        return

    if not card.photo.telegram_file_id:
        await safe_edit_text(
            callback.message,
            text="У отчета нет доступного фото.",
            reply_markup=client_meal_report_card_keyboard(
                report_id=card.report.id,
                can_reply=card.report.status == "needs_clarification",
            ),
        )
        return

    caption = format_client_meal_report_caption(card)

    await safe_edit_text(callback.message, text="Открываю отчет...")

    await callback.bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=card.photo.telegram_file_id,
        caption=caption,
        reply_markup=client_meal_report_card_keyboard(
            report_id=card.report.id,
            can_reply=card.report.status == "needs_clarification",
        ),
    )


@router.callback_query(ReplyMealReportCallback.filter())
async def start_clarification_response_handler(
    callback: CallbackQuery,
    callback_data: ReplyMealReportCallback,
    state: FSMContext,
) -> None:
    report_id = callback_data.report_id
    language_code = await get_user_language(callback.from_user.id)

    await state.set_state(MealReportStates.waiting_for_clarification_response)
    await state.update_data(report_id=report_id)

    await callback.answer()
    await callback.message.answer(
        f"Напишите ответ тренеру по этому отчету.\n\n"
        f"Если хотите отменить действие, нажмите {t('common.cancel', language_code)} или используйте /cancel.",
        reply_markup=cancel_keyboard(language_code),
    )


@router.message(MealReportStates.waiting_for_clarification_response)
async def process_clarification_response_handler(
    message: Message,
    state: FSMContext,
) -> None:
    response_text = (message.text or "").strip()

    data = await state.get_data()
    report_id = data.get("report_id")

    if not report_id:
        await state.clear()
        await message.answer("Не удалось определить отчет. Откройте отчет заново.")
        return

    result = await respond_to_meal_report_clarification(
        telegram_id=message.from_user.id,
        report_id=report_id,
        response_text=response_text,
    )

    if not result.ok:
        if result.reason == "response_too_short":
            await message.answer("Ответ слишком короткий. Напишите минимум 2 символа.")
            return

        if result.reason == "response_too_long":
            await message.answer("Ответ слишком длинный. Напишите до 1000 символов.")
            return

        await state.clear()

        if result.reason == "report_not_waiting_for_clarification":
            await message.answer("Этот отчет сейчас не ожидает уточнения.")
            return

        if result.reason == "report_not_found":
            await message.answer("Отчет не найден или у вас нет доступа.")
            return

        if result.reason == "client_not_found":
            await message.answer("Не удалось найти активный профиль клиента.")
            return

        await message.answer("Не удалось отправить ответ.")
        return

    await state.clear()

    await message.answer("Ответ отправлен тренеру. Отчет снова отправлен на проверку.")

    if result.coach_telegram_id is not None:
        await send_logged_message(
            bot=message.bot,
            chat_id=result.coach_telegram_id,
            notification_type="clarification_answered",
            related_entity_type="meal_report",
            related_entity_id=result.report_id,
            text=(
                "Клиент ответил на уточнение по отчету еды.\n\n"
                f"Клиент: {result.client_display_name or 'без имени'}\n"
                f"Ответ:\n{result.response_text}\n\n"
                "Откройте раздел “🍽 Отчеты еды”, чтобы проверить отчет снова."
            ),
        )

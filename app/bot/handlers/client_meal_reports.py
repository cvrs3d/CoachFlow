from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

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
from app.bot.handlers.meal_report_labels import (
    CLIENT_REPORT_FILTER_LABELS,
    REPORT_STATUS_LABELS,
    MEAL_TYPE_LABELS,
    VERDICT_LABELS
)
from app.services.notifications import send_logged_message

router = Router()

@router.message(F.text == "🍽 Мои отчеты еды")
async def my_meal_reports_handler(message: Message) -> None:
    await message.answer(
        "Выберите раздел отчетов еды:",
        reply_markup=client_meal_reports_filter_keyboard(),
    )

@router.callback_query(F.data == "mr:cfilters")
async def client_meal_reports_filters_callback_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        "Выберите раздел отчетов еды:",
        reply_markup=client_meal_reports_filter_keyboard(),
    )

@router.callback_query(F.data.startswith("mr:cf:"))
async def client_meal_reports_by_filter_handler(callback: CallbackQuery) -> None:
    report_filter = callback.data.split(":", 2)[2]

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

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        "Выберите раздел отчетов еды:",
        reply_markup=client_meal_reports_filter_keyboard(),
    )


@router.callback_query(F.data.startswith("mr:co:"))
async def open_client_meal_report_handler(callback: CallbackQuery) -> None:
    report_id = callback.data.split(":", 2)[2]

    card = await get_meal_report_for_client(
        telegram_id=callback.from_user.id,
        report_id=report_id,
    )

    await callback.answer()

    if card is None:
        await safe_edit_text(callback.message,
            text="Отчет не найден или у вас нет доступа."
        )
        return

    meal_type_label = MEAL_TYPE_LABELS.get(
        card.report.meal_type,
        card.report.meal_type,
    )

    status_label = REPORT_STATUS_LABELS.get(
        card.report.status,
        card.report.status,
    )

    caption = (
        "Ваш отчет еды\n\n"
        f"Прием пищи: {meal_type_label}\n"
        f"Статус: {status_label}"
    )

    if card.report.client_comment:
        caption += f"\n\nВаш комментарий:\n{card.report.client_comment}"

    if card.review is not None:
        verdict_label = VERDICT_LABELS.get(card.review.verdict, card.review.verdict)

        caption += (
            "\n\nПроверка тренера:"
            f"\nРезультат: {verdict_label}"
        )

        if card.review.comment:
            caption += f"\nКомментарий:\n{card.review.comment}"

        
    if card.report.clarification_response:
        caption += f"\n\nВаш ответ тренеру:\n{card.report.clarification_response}"

    if not card.photo.telegram_file_id:
        await safe_edit_text(callback.message,
            text="У отчета нет доступного фото.",
            reply_markup=client_meal_report_card_keyboard(
                report_id=card.report.id,
                can_reply=card.report.status == "needs_clarification",
            ),
        )
        return

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

@router.callback_query(F.data.startswith("mr:reply:"))
async def start_clarification_response_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    report_id = callback.data.split(":", 2)[2]

    await state.set_state(MealReportStates.waiting_for_clarification_response)
    await state.update_data(report_id=report_id)

    await callback.answer()

    await callback.message.answer(
        "Напишите ответ тренеру по этому отчету."
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

    await message.answer(
        "Ответ отправлен тренеру. Отчет снова отправлен на проверку."
    )

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
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.meal_reports import (
    client_meal_report_card_keyboard,
    client_meal_reports_keyboard,
    coach_meal_reports_filter_keyboard,
    meal_review_keyboard,
    meal_type_keyboard,
    pending_meal_reports_keyboard,
    client_meal_reports_filter_keyboard,
)
from app.bot.states.meal_reports import MealReportStates
from app.services.meal_reports import (
    create_meal_report_from_photo,
    get_meal_report_for_client,
    get_meal_report_for_coach,
    list_meal_reports_for_client,
    list_meal_reports_for_client_by_filter,
    list_meal_reports_for_coach_by_filter,
    list_pending_meal_reports_for_coach,
    review_meal_report,
    respond_to_meal_report_clarification,
)
from app.bot.utils.safe_messages import (
    safe_answer_or_edit_text,
    safe_edit_reply_markup,
    safe_edit_text,
)
from app.services.notifications import send_logged_message

router = Router()

COACH_REPORT_FILTER_LABELS = {
    "pending": "Отчеты на проверку",
    "clarification": "Отчеты, ожидающие уточнения клиента",
    "reviewed": "Проверенные отчеты",
}

MEAL_TYPE_LABELS = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "dinner": "Ужин",
    "snack": "Перекус",
    "other": "Другое",
}

CLIENT_REPORT_FILTER_LABELS = {
    "all": "Все отчеты еды",
    "pending": "Отчеты на проверке",
    "reviewed": "Проверенные отчеты",
    "clarification": "Отчеты, где нужно уточнение",
}


@router.message(F.text == "🍽 Отправить фото еды")
async def start_meal_report_handler(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()

    await message.answer(
        "Выберите прием пищи:",
        reply_markup=meal_type_keyboard(),
    )


@router.callback_query(F.data.startswith("mr:t:"))
async def choose_meal_type_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    meal_type = callback.data.split(":", 2)[2]

    if meal_type not in MEAL_TYPE_LABELS:
        await callback.answer("Неизвестный тип приема пищи.", show_alert=True)
        return

    await state.update_data(meal_type=meal_type)
    await state.set_state(MealReportStates.waiting_for_photo)

    await callback.answer()

    await safe_edit_text(callback.message,
        text="Прием пищи выбран: "
        f"{MEAL_TYPE_LABELS[meal_type]}\n\n"
        "Теперь отправьте фото еды.\n"
        "Можно добавить подпись к фото, если хотите."
    )


@router.message(MealReportStates.waiting_for_photo, F.photo)
async def process_meal_photo_handler(
    message: Message,
    state: FSMContext,
) -> None:
    data = await state.get_data()
    meal_type = data.get("meal_type")

    if meal_type is None:
        await state.clear()
        await message.answer("Не удалось определить тип приема пищи. Начните заново.")
        return

    photo = message.photo[-1]
    client_comment = message.caption

    result = await create_meal_report_from_photo(
        telegram_id=message.from_user.id,
        meal_type=meal_type,
        telegram_file_id=photo.file_id,
        telegram_file_unique_id=photo.file_unique_id,
        client_comment=client_comment,
    )

    await state.clear()

    if not result.ok:
        if result.reason == "client_not_found":
            await message.answer("Не удалось найти активный профиль клиента.")
            return

        if result.reason == "invalid_meal_type":
            await message.answer("Некорректный тип приема пищи.")
            return

        await message.answer("Не удалось отправить отчет.")
        return

    await message.answer("Отчет отправлен тренеру на проверку.")

    if result.coach_telegram_id is not None:
        meal_type_label = MEAL_TYPE_LABELS.get(
            result.meal_type or "",
            result.meal_type or "не указан",
        )

        await send_logged_message(
            bot=message.bot,
            chat_id=result.coach_telegram_id,
            notification_type="meal_report_submitted",
            related_entity_type="meal_report",
            related_entity_id=result.report_id,
            text=(
                "Новый отчет еды.\n\n"
                f"Клиент: {result.client_display_name or 'без имени'}\n"
                f"Прием пищи: {meal_type_label}\n\n"
                "Откройте раздел “🍽 Отчеты еды”, чтобы проверить отчет."
            ),
        )


@router.message(MealReportStates.waiting_for_photo)
async def process_wrong_meal_photo_handler(message: Message) -> None:
    await message.answer(
        "Пожалуйста, отправьте именно фото еды.\n\n"
        "Если хотите отменить действие, используйте /cancel."
    )

VERDICT_LABELS = {
    "ok": "Хорошо ✅",
    "needs_improvement": "Нужно улучшить ⚠️",
    "question": "Нужно уточнение ❓",
}


@router.message(F.text == "🍽 Отчеты еды")
async def meal_reports_filters_handler(message: Message) -> None:
    await message.answer(
        "Выберите раздел отчетов еды:",
        reply_markup=coach_meal_reports_filter_keyboard(),
    )

@router.callback_query(F.data == "mr:filters")
async def meal_reports_filters_callback_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback.message.answer(
        "Выберите раздел отчетов еды:",
        reply_markup=coach_meal_reports_filter_keyboard(),
    )

@router.callback_query(F.data.startswith("mr:f:"))
async def coach_meal_reports_by_filter_handler(callback: CallbackQuery) -> None:
    report_filter = callback.data.split(":", 2)[2]

    reports = await list_meal_reports_for_coach_by_filter(
        telegram_id=callback.from_user.id,
        report_filter=report_filter,
        limit=10,
    )

    await callback.answer()

    title = COACH_REPORT_FILTER_LABELS.get(report_filter, "Отчеты еды")

    if not reports:
        await safe_edit_text(callback.message,
            text=f"{title}.\n\nСписок пуст.",
            reply_markup=coach_meal_reports_filter_keyboard(),
        )
        return

    await safe_edit_text(callback.message, 
        text=f"{title}:",
        reply_markup=pending_meal_reports_keyboard(reports),
    )


@router.callback_query(F.data == "mr:list")
async def pending_meal_reports_callback_handler(callback: CallbackQuery) -> None:
    reports = await list_meal_reports_for_coach_by_filter(
        telegram_id=callback.from_user.id,
        report_filter="pending",
        limit=10,
    )

    await callback.answer()

    await safe_edit_reply_markup(callback.message, reply_markup=None)

    if not reports:
        await callback.message.answer("Нет отчетов еды на проверку.")
        return

    await callback.message.answer(
        "Отчеты еды на проверку:",
        reply_markup=pending_meal_reports_keyboard(reports),
    )

@router.callback_query(F.data.startswith("mr:o:"))
async def open_meal_report_handler(callback: CallbackQuery) -> None:
    report_id = callback.data.split(":", 2)[2]

    card = await get_meal_report_for_coach(
        telegram_id=callback.from_user.id,
        report_id=report_id,
    )

    await callback.answer()

    if card is None:
        await safe_edit_text(callback.message, "Отчет не найден или у вас нет доступа.")
        return

    meal_type_label = MEAL_TYPE_LABELS.get(
        card.report.meal_type,
        card.report.meal_type,
    )

    client_name = card.client.display_name or "без имени"

    caption = (
        f"Отчет еды\n\n"
        f"Клиент: {client_name}\n"
        f"Прием пищи: {meal_type_label}\n"
        f"Статус: {card.report.status}"
    )

    if card.report.client_comment:
        caption += f"\n\nКомментарий клиента:\n{card.report.client_comment}"

    if not card.photo.telegram_file_id:
        await safe_edit_text(callback.message,
            text="У отчета нет доступного Telegram file_id."
        )
        return

    await safe_edit_text(callback.message,
        text="Открываю отчет..."
    )

    await callback.bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=card.photo.telegram_file_id,
        caption=caption,
        reply_markup=meal_review_keyboard(card.report.id),
    )


@router.callback_query(F.data.startswith("mr:ok:"))
async def review_meal_report_ok_handler(callback: CallbackQuery) -> None:
    report_id = callback.data.split(":", 2)[2]
    await process_meal_report_review(callback, report_id, "ok")


@router.callback_query(F.data.startswith("mr:ni:"))
async def review_meal_report_needs_improvement_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    report_id = callback.data.split(":", 2)[2]

    await state.set_state(MealReportStates.waiting_for_review_comment)
    await state.update_data(
        report_id=report_id,
        verdict="needs_improvement",
    )

    await callback.answer()

    await callback.message.answer(
        "Напишите комментарий для клиента: что нужно улучшить?"
    )


@router.callback_query(F.data.startswith("mr:q:"))
async def review_meal_report_question_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    report_id = callback.data.split(":", 2)[2]

    await state.set_state(MealReportStates.waiting_for_review_comment)
    await state.update_data(
        report_id=report_id,
        verdict="question",
    )

    await callback.answer()

    await callback.message.answer(
        "Напишите вопрос или уточнение для клиента."
    )


async def process_meal_report_review(
    callback: CallbackQuery,
    report_id: str,
    verdict: str,
    comment: str | None = None,
) -> None:
    result = await review_meal_report(
        telegram_id=callback.from_user.id,
        report_id=report_id,
        verdict=verdict,
        comment=comment,
    )

    await callback.answer()

    if not result.ok:
        if result.reason == "report_already_reviewed":
            await callback.message.answer("Этот отчет уже проверен.")
            return

        if result.reason == "report_not_found":
            await callback.message.answer("Отчет не найден или у вас нет доступа.")
            return

        await callback.message.answer("Не удалось проверить отчет.")
        return

    verdict_label = VERDICT_LABELS.get(verdict, verdict)

    if callback.message.caption is not None:
        try:
            await callback.message.edit_caption(
                caption=(
                    f"{callback.message.caption}\n\n"
                    f"Проверено: {verdict_label}"
                ),
                reply_markup=None,
            )
        except Exception:
            await callback.message.answer(f"Отчет проверен: {verdict_label}")
    else:
        await callback.message.answer(f"Отчет проверен: {verdict_label}")

    if result.client_telegram_id is not None:
        client_text = (
            "Тренер проверил ваш отчет еды.\n\n"
            f"Результат: {verdict_label}"
        )

        if result.comment:
            client_text += f"\n\nКомментарий тренера:\n{result.comment}"

        await send_logged_message(
            bot=callback.bot,
            chat_id=result.client_telegram_id,
            notification_type="meal_report_reviewed",
            related_entity_type="meal_report",
            related_entity_id=report_id,
            text=client_text,
        )

@router.message(MealReportStates.waiting_for_review_comment)
async def process_meal_review_comment_handler(
    message: Message,
    state: FSMContext,
) -> None:
    comment = (message.text or "").strip()

    if len(comment) < 2:
        await message.answer("Комментарий слишком короткий. Напишите минимум 2 символа.")
        return

    if len(comment) > 1000:
        await message.answer("Комментарий слишком длинный. Напишите до 1000 символов.")
        return

    data = await state.get_data()
    report_id = data.get("report_id")
    verdict = data.get("verdict")

    if not report_id or not verdict:
        await state.clear()
        await message.answer("Не удалось определить отчет. Откройте отчет заново.")
        return

    result = await review_meal_report(
        telegram_id=message.from_user.id,
        report_id=report_id,
        verdict=verdict,
        comment=comment,
    )

    await state.clear()

    if not result.ok:
        if result.reason == "report_already_reviewed":
            await message.answer("Этот отчет уже проверен.")
            return

        if result.reason == "report_not_found":
            await message.answer("Отчет не найден или у вас нет доступа.")
            return

        await message.answer("Не удалось проверить отчет.")
        return

    verdict_label = VERDICT_LABELS.get(verdict, verdict)

    await message.answer(
        f"Отчет проверен: {verdict_label}\n\n"
        f"Комментарий отправлен клиенту:\n{comment}"
    )

    notification_type = (
        "clarification_requested"
        if verdict == "question"
        else "meal_report_reviewed"
    )

    if result.client_telegram_id is not None:
        await send_logged_message(
            bot=message.bot,
            chat_id=result.client_telegram_id,
            notification_type=notification_type,
            related_entity_type="meal_report",
            related_entity_id=report_id,
            text=(
                "Тренер проверил ваш отчет еды.\n\n"
                f"Результат: {verdict_label}\n\n"
                f"Комментарий тренера:\n{comment}"
            ),
        )

REPORT_STATUS_LABELS = {
    "draft": "Черновик",
    "submitted": "На проверке",
    "in_review": "На проверке",
    "reviewed": "Проверен",
    "needs_clarification": "Нужно уточнение",
    "archived": "Архив",
}


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
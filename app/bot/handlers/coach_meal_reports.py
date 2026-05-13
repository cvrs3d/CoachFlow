from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.meal_reports import (
    CoachMealReportFilterCallback,
    OpenCoachMealReportCallback,
    ReviewMealReportCallback,
)
from app.bot.formatters.meal_reports import (
    format_coach_meal_report_caption,
)
from app.bot.handlers.meal_report_labels import (
    COACH_REPORT_FILTER_LABELS,
    VERDICT_LABELS,
)
from app.bot.keyboards.meal_reports import (
    coach_meal_reports_filter_keyboard,
    meal_review_keyboard,
    pending_meal_reports_keyboard,
)
from app.bot.states.meal_reports import MealReportStates
from app.bot.utils.safe_messages import (
    safe_edit_caption,
    safe_edit_reply_markup,
    safe_edit_text,
)
from app.services.meal_reports import (
    get_meal_report_for_coach,
    list_meal_reports_for_coach_by_filter,
    review_meal_report,
)
from app.services.notifications import send_logged_message

router = Router()


@router.message(F.text == "🍽 Отчеты еды")
async def meal_reports_filters_handler(message: Message) -> None:
    await message.answer(
        "Выберите раздел отчетов еды:",
        reply_markup=coach_meal_reports_filter_keyboard(),
    )


@router.callback_query(F.data == "mr:filters")
async def meal_reports_filters_callback_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    await safe_edit_reply_markup(callback.message, reply_markup=None)

    await callback.message.answer(
        "Выберите раздел отчетов еды:",
        reply_markup=coach_meal_reports_filter_keyboard(),
    )


@router.callback_query(CoachMealReportFilterCallback.filter())
async def coach_meal_reports_by_filter_handler(
    callback: CallbackQuery,
    callback_data: CoachMealReportFilterCallback,
) -> None:
    report_filter = callback_data.report_filter

    reports = await list_meal_reports_for_coach_by_filter(
        telegram_id=callback.from_user.id,
        report_filter=report_filter,
        limit=10,
    )

    await callback.answer()

    title = COACH_REPORT_FILTER_LABELS.get(report_filter, "Отчеты еды")

    if not reports:
        await safe_edit_text(
            callback.message,
            text=f"{title}.\n\nСписок пуст.",
            reply_markup=coach_meal_reports_filter_keyboard(),
        )
        return

    await safe_edit_text(
        callback.message,
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


@router.callback_query(OpenCoachMealReportCallback.filter())
async def open_meal_report_handler(
    callback: CallbackQuery,
    callback_data: OpenCoachMealReportCallback,
) -> None:
    report_id = callback_data.report_id

    card = await get_meal_report_for_coach(
        telegram_id=callback.from_user.id,
        report_id=report_id,
    )

    await callback.answer()

    if card is None:
        await safe_edit_text(callback.message, "Отчет не найден или у вас нет доступа.")
        return

    caption = format_coach_meal_report_caption(card)

    if not card.photo.telegram_file_id:
        await safe_edit_text(callback.message, text="У отчета нет доступного Telegram file_id.")
        return

    await safe_edit_text(callback.message, text="Открываю отчет...")

    await callback.bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=card.photo.telegram_file_id,
        caption=caption,
        reply_markup=meal_review_keyboard(card.report.id),
    )


@router.callback_query(ReviewMealReportCallback.filter())
async def review_meal_report_handler(
    callback: CallbackQuery,
    callback_data: ReviewMealReportCallback,
    state: FSMContext,
) -> None:
    report_id = callback_data.report_id
    action = callback_data.action

    if action == "ok":
        await process_meal_report_review(callback, report_id, "ok")
        return

    if action == "needs_improvement":
        await state.set_state(MealReportStates.waiting_for_review_comment)
        await state.update_data(
            report_id=report_id,
            verdict="needs_improvement",
        )

        await callback.answer()
        await callback.message.answer(
            "Напишите комментарий для клиента: что нужно улучшить?"
        )
        return

    if action == "question":
        await state.set_state(MealReportStates.waiting_for_review_comment)
        await state.update_data(
            report_id=report_id,
            verdict="question",
        )

        await callback.answer()
        await callback.message.answer(
            "Напишите вопрос или уточнение для клиента."
        )
        return

    await callback.answer("Неизвестное действие.", show_alert=True)


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
        edited = await safe_edit_caption(
            callback.message,
            caption=(f"{callback.message.caption}\n\nПроверено: {verdict_label}"),
            reply_markup=None,
        )

        if not edited:
            await callback.message.answer(f"Отчет проверен: {verdict_label}")
    else:
        await callback.message.answer(f"Отчет проверен: {verdict_label}")

    if result.client_telegram_id is not None:
        client_text = f"Тренер проверил ваш отчет еды.\n\nРезультат: {verdict_label}"

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
        f"Отчет проверен: {verdict_label}\n\nКомментарий отправлен клиенту:\n{comment}"
    )

    notification_type = (
        "clarification_requested" if verdict == "question" else "meal_report_reviewed"
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

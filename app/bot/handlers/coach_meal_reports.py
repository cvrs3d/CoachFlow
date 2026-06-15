from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.meal_reports import (
    CoachMealReportFilterCallback,
    OpenCoachMealReportCallback,
    ReviewMealReportCallback,
)
from app.bot.callbacks.menu import MainMenuCallback
from app.bot.i18n import get_user_language, t
from app.bot.formatters.meal_reports import (
    format_coach_meal_report_caption,
)
from app.bot.handlers.meal_report_labels import (
    get_coach_report_filter_label,
    get_verdict_label,
)
from app.bot.keyboards.common import cancel_keyboard
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


@router.callback_query(MainMenuCallback.filter(F.action == "coach_meal_reports"))
async def meal_reports_filters_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    await callback.answer()

    await callback.message.answer(
        t("meal_reports.coach_choose_section", language_code),
        reply_markup=coach_meal_reports_filter_keyboard(language_code),
    )


@router.callback_query(F.data == "mr:filters")
async def meal_reports_filters_callback_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    await callback.answer()

    await safe_edit_reply_markup(callback.message, reply_markup=None)

    await callback.message.answer(
        t("meal_reports.coach_choose_section", language_code),
        reply_markup=coach_meal_reports_filter_keyboard(language_code),
    )


@router.callback_query(CoachMealReportFilterCallback.filter())
async def coach_meal_reports_by_filter_handler(
    callback: CallbackQuery,
    callback_data: CoachMealReportFilterCallback,
) -> None:
    report_filter = callback_data.report_filter
    language_code = await get_user_language(callback.from_user.id)

    reports = await list_meal_reports_for_coach_by_filter(
        telegram_id=callback.from_user.id,
        report_filter=report_filter,
        limit=10,
    )

    await callback.answer()

    title = get_coach_report_filter_label(report_filter, language_code)

    if not reports:
        await safe_edit_text(
            callback.message,
            text=f"{title}.\n\n{t('meal_reports.empty', language_code)}",
            reply_markup=coach_meal_reports_filter_keyboard(language_code),
        )
        return

    await safe_edit_text(
        callback.message,
        text=f"{title}:",
        reply_markup=pending_meal_reports_keyboard(reports, language_code),
    )


@router.callback_query(F.data == "mr:list")
async def pending_meal_reports_callback_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    reports = await list_meal_reports_for_coach_by_filter(
        telegram_id=callback.from_user.id,
        report_filter="pending",
        limit=10,
    )

    await callback.answer()

    await safe_edit_reply_markup(callback.message, reply_markup=None)

    if not reports:
        await callback.message.answer(t("meal_reports.no_pending", language_code))
        return

    await callback.message.answer(
        t("meal_reports.coach_choose_section", language_code),
        reply_markup=pending_meal_reports_keyboard(reports, language_code),
    )


@router.callback_query(OpenCoachMealReportCallback.filter())
async def open_meal_report_handler(
    callback: CallbackQuery,
    callback_data: OpenCoachMealReportCallback,
) -> None:
    report_id = callback_data.report_id
    language_code = await get_user_language(callback.from_user.id)

    card = await get_meal_report_for_coach(
        telegram_id=callback.from_user.id,
        report_id=report_id,
    )

    await callback.answer()

    if card is None:
        await safe_edit_text(callback.message, t("meal_reports.open_failed", language_code))
        return

    caption = format_coach_meal_report_caption(card, language_code)

    if not card.photo.telegram_file_id:
        await safe_edit_text(callback.message, text=t("meal_reports.no_file_id", language_code))
        return

    await safe_edit_text(callback.message, text=t("meal_reports.opening_coach", language_code))

    await callback.bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=card.photo.telegram_file_id,
        caption=caption,
        reply_markup=meal_review_keyboard(card.report.id, language_code),
    )


@router.callback_query(ReviewMealReportCallback.filter())
async def review_meal_report_handler(
    callback: CallbackQuery,
    callback_data: ReviewMealReportCallback,
    state: FSMContext,
) -> None:
    language_code = await get_user_language(callback.from_user.id)
    report_id = callback_data.report_id
    action = callback_data.action

    if action == "ok":
        await process_meal_report_review(callback, report_id, "ok")
        return

    if action == "needs_improvement":
        language_code = await get_user_language(callback.from_user.id)
        await state.set_state(MealReportStates.waiting_for_review_comment)
        await state.update_data(
            report_id=report_id,
            verdict="needs_improvement",
        )

        await callback.answer()
        await callback.message.answer(
            f"{t('meal_reports.comment_prompt', language_code)}\n\n{t('common.cancel', language_code)} /cancel",
            reply_markup=cancel_keyboard(language_code),
        )
        return

    if action == "question":
        language_code = await get_user_language(callback.from_user.id)
        await state.set_state(MealReportStates.waiting_for_review_comment)
        await state.update_data(
            report_id=report_id,
            verdict="question",
        )

        await callback.answer()
        await callback.message.answer(
            f"{t('meal_reports.question_prompt', language_code)}\n\n{t('common.cancel', language_code)} /cancel",
            reply_markup=cancel_keyboard(language_code),
        )
        return

    await callback.answer(t("meal_reports.unknown_action", language_code), show_alert=True)


async def process_meal_report_review(
    callback: CallbackQuery,
    report_id: str,
    verdict: str,
    comment: str | None = None,
) -> None:
    language_code = await get_user_language(callback.from_user.id)
    result = await review_meal_report(
        telegram_id=callback.from_user.id,
        report_id=report_id,
        verdict=verdict,
        comment=comment,
    )

    await callback.answer()

    if not result.ok:
        if result.reason == "report_already_reviewed":
            await callback.message.answer(t("meal_reports.already_reviewed", language_code))
            return

        if result.reason == "report_not_found":
            await callback.message.answer(t("meal_reports.report_not_found", language_code))
            return

        await callback.message.answer(t("meal_reports.review_failed", language_code))
        return

    verdict_label = get_verdict_label(verdict, language_code)

    if callback.message.caption is not None:
        edited = await safe_edit_caption(
            callback.message,
            caption=(f"{callback.message.caption}\n\n{t('meal_reports.reviewed_status', language_code, verdict_label=verdict_label)}"),
            reply_markup=None,
        )

        if not edited:
            await callback.message.answer(t("meal_reports.reviewed", language_code, verdict_label=verdict_label))
    else:
        await callback.message.answer(t("meal_reports.reviewed", language_code, verdict_label=verdict_label))

    if result.client_telegram_id is not None:
        client_language_code = await get_user_language(result.client_telegram_id)
        if result.comment:
            client_text = t(
                "meal_reports.reviewed_client_with_comment",
                client_language_code,
                verdict_label=verdict_label,
                comment=result.comment,
            )
        else:
            client_text = t(
                "meal_reports.reviewed_client",
                client_language_code,
                verdict_label=verdict_label,
            )

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
    language_code = await get_user_language(message.from_user.id)
    comment = (message.text or "").strip()
    language_code = await get_user_language(message.from_user.id)

    if len(comment) < 2:
        await message.answer(t("meal_reports.short_comment", language_code))
        return

    if len(comment) > 1000:
        await message.answer(t("meal_reports.long_comment", language_code))
        return

    data = await state.get_data()
    report_id = data.get("report_id")
    verdict = data.get("verdict")

    if not report_id or not verdict:
        await state.clear()
        await message.answer(t("meal_reports.report_unknown", language_code))
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
            await message.answer(t("meal_reports.already_reviewed", language_code))
            return

        if result.reason == "report_not_found":
            await message.answer(t("meal_reports.report_not_found", language_code))
            return

        await message.answer(t("meal_reports.review_failed", language_code))
        return

    verdict_label = get_verdict_label(verdict, language_code)

    await message.answer(
        t("meal_reports.reviewed_comment", language_code, verdict_label=verdict_label, comment=comment)
    )

    notification_type = (
        "clarification_requested" if verdict == "question" else "meal_report_reviewed"
    )

    if result.client_telegram_id is not None:
        client_language_code = await get_user_language(result.client_telegram_id)
        if result.comment:
            client_text = t(
                "meal_reports.reviewed_client_with_comment",
                client_language_code,
                verdict_label=verdict_label,
                comment=result.comment,
            )
        else:
            client_text = t(
                "meal_reports.reviewed_client",
                client_language_code,
                verdict_label=verdict_label,
            )
        await send_logged_message(
            bot=message.bot,
            chat_id=result.client_telegram_id,
            notification_type=notification_type,
            related_entity_type="meal_report",
            related_entity_id=report_id,
            text=client_text,
        )

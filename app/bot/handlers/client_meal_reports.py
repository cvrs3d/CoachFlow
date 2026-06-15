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
from app.bot.handlers.meal_report_labels import get_client_report_filter_label
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
    language_code = await get_user_language(callback.from_user.id)
    await callback.answer()

    await callback.message.answer(
        t("meal_reports.choose_section", language_code),
        reply_markup=client_meal_reports_filter_keyboard(language_code),
    )

@router.callback_query(F.data == "mr:cfilters")
async def client_meal_reports_filters_callback_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    await callback.answer()

    await safe_edit_reply_markup(callback.message, reply_markup=None)

    await callback.message.answer(
        t("meal_reports.choose_section", language_code),
        reply_markup=client_meal_reports_filter_keyboard(language_code),
    )


@router.callback_query(ClientMealReportFilterCallback.filter())
async def client_meal_reports_by_filter_handler(
    callback: CallbackQuery,
    callback_data: ClientMealReportFilterCallback,
) -> None:
    report_filter = callback_data.report_filter
    language_code = await get_user_language(callback.from_user.id)

    reports = await list_meal_reports_for_client_by_filter(
        telegram_id=callback.from_user.id,
        report_filter=report_filter,
        limit=10,
    )

    await callback.answer()

    title = get_client_report_filter_label(report_filter, language_code)

    if not reports:
        await safe_answer_or_edit_text(
            callback.message,
            f"{title}.\n\n{t('meal_reports.empty', language_code)}",
            reply_markup=client_meal_reports_filter_keyboard(language_code),
        )
        return

    await safe_answer_or_edit_text(
        callback.message,
        f"{title}:",
        reply_markup=client_meal_reports_keyboard(reports, language_code),
    )


@router.callback_query(F.data == "mr:clist")
async def my_meal_reports_callback_handler(callback: CallbackQuery) -> None:
    language_code = await get_user_language(callback.from_user.id)
    await callback.answer()

    await safe_edit_reply_markup(callback.message, reply_markup=None)

    await callback.message.answer(
        t("meal_reports.choose_section", language_code),
        reply_markup=client_meal_reports_filter_keyboard(language_code),
    )


@router.callback_query(OpenClientMealReportCallback.filter())
async def open_client_meal_report_handler(
    callback: CallbackQuery,
    callback_data: OpenClientMealReportCallback,
) -> None:
    report_id = callback_data.report_id
    language_code = await get_user_language(callback.from_user.id)

    card = await get_meal_report_for_client(
        telegram_id=callback.from_user.id,
        report_id=report_id,
    )

    await callback.answer()

    if card is None:
        await safe_edit_text(callback.message, text=t("meal_reports.report_not_found", language_code))
        return

    if not card.photo.telegram_file_id:
        await safe_edit_text(
            callback.message,
            text=t("meal_reports.no_photo", language_code),
            reply_markup=client_meal_report_card_keyboard(
                report_id=card.report.id,
                can_reply=card.report.status == "needs_clarification",
                language_code=language_code,
            ),
        )
        return

    caption = format_client_meal_report_caption(card, language_code)

    await safe_edit_text(callback.message, text=t("meal_reports.opening", language_code))

    await callback.bot.send_photo(
        chat_id=callback.message.chat.id,
        photo=card.photo.telegram_file_id,
        caption=caption,
        reply_markup=client_meal_report_card_keyboard(
            report_id=card.report.id,
            can_reply=card.report.status == "needs_clarification",
            language_code=language_code,
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
        f"{t('meal_reports.reply_prompt', language_code)}\n\n{t('common.cancel', language_code)} /cancel",
        reply_markup=cancel_keyboard(language_code),
    )


@router.message(MealReportStates.waiting_for_clarification_response)
async def process_clarification_response_handler(
    message: Message,
    state: FSMContext,
) -> None:
    language_code = await get_user_language(message.from_user.id)
    response_text = (message.text or "").strip()

    data = await state.get_data()
    report_id = data.get("report_id")

    if not report_id:
        await state.clear()
        await message.answer(t("meal_reports.report_unknown", language_code))
        return

    result = await respond_to_meal_report_clarification(
        telegram_id=message.from_user.id,
        report_id=report_id,
        response_text=response_text,
    )

    if not result.ok:
        if result.reason == "response_too_short":
            await message.answer(t("meal_reports.short_response", language_code))
            return

        if result.reason == "response_too_long":
            await message.answer(t("meal_reports.long_response", language_code))
            return

        await state.clear()

        if result.reason == "report_not_waiting_for_clarification":
            await message.answer(t("meal_reports.not_waiting", language_code))
            return

        if result.reason == "report_not_found":
            await message.answer(t("meal_reports.report_not_found", language_code))
            return

        if result.reason == "client_not_found":
            await message.answer(t("meal_reports.client_not_found", language_code))
            return

        await message.answer(t("meal_reports.send_failed", language_code))
        return

    await state.clear()

    await message.answer(t("meal_reports.sent", language_code))

    if result.coach_telegram_id is not None:
        coach_language_code = await get_user_language(result.coach_telegram_id)
        await send_logged_message(
            bot=message.bot,
            chat_id=result.coach_telegram_id,
            notification_type="clarification_answered",
            related_entity_type="meal_report",
            related_entity_id=result.report_id,
            text=t(
                "meal_reports.notification",
                coach_language_code,
                client_name=result.client_display_name or t("clients.without_name", coach_language_code),
                response_text=result.response_text,
            ),
        )

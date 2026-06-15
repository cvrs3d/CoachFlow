from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks.meal_reports import MealTypeCallback
from app.bot.callbacks.menu import MainMenuCallback
from app.bot.i18n import get_user_language, t
from app.bot.keyboards.common import cancel_keyboard
from app.bot.handlers.meal_report_labels import MEAL_TYPE_LABELS
from app.bot.keyboards.meal_reports import meal_type_keyboard
from app.bot.states.meal_reports import MealReportStates
from app.bot.utils.safe_messages import safe_edit_text
from app.services.meal_reports import create_meal_report_from_photo
from app.services.notifications import send_logged_message

router = Router()


@router.callback_query(MainMenuCallback.filter(F.action == "client_meal_submit"))
async def start_meal_report_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    language_code = await get_user_language(callback.from_user.id)
    await state.clear()
    await callback.answer()

    await callback.message.answer(
        t("meal_reports.choose_meal_type", language_code),
        reply_markup=meal_type_keyboard(language_code),
    )


@router.callback_query(MealTypeCallback.filter())
async def choose_meal_type_handler(
    callback: CallbackQuery,
    callback_data: MealTypeCallback,
    state: FSMContext,
) -> None:
    meal_type = callback_data.meal_type
    language_code = await get_user_language(callback.from_user.id)

    if meal_type not in MEAL_TYPE_LABELS:
        await callback.answer(t("meal_reports.unknown_meal_type", language_code), show_alert=True)
        return

    await state.update_data(meal_type=meal_type)
    await state.set_state(MealReportStates.waiting_for_photo)

    await callback.answer()

    await safe_edit_text(
        callback.message,
        text=(
            f"{t('meal_reports.meal_type_selected', language_code, meal_type_label=MEAL_TYPE_LABELS[meal_type])}\n\n"
            f"{t('meal_reports.send_photo_prompt', language_code)}"
        ),
        reply_markup=cancel_keyboard(language_code),
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
        await message.answer(t("meal_reports.meal_type_unknown_restart", language_code))
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
            await message.answer(t("meal_reports.client_not_found", language_code))
            return

        if result.reason == "invalid_meal_type":
            await message.answer(t("meal_reports.invalid_meal_type", language_code))
            return

        await message.answer(t("meal_reports.send_failed", language_code))
        return

    await message.answer(t("meal_reports.sent_to_coach", language_code))

    if result.coach_telegram_id is not None:
        coach_language_code = await get_user_language(result.coach_telegram_id)
        meal_type_label = MEAL_TYPE_LABELS.get(
            result.meal_type or "",
            result.meal_type or t("clients.without_name", coach_language_code),
        )

        await send_logged_message(
            bot=message.bot,
            chat_id=result.coach_telegram_id,
            notification_type="meal_report_submitted",
            related_entity_type="meal_report",
            related_entity_id=result.report_id,
            text=(
                f"{t('meal_reports.coach_notification_title', coach_language_code)}\n\n"
                f"{t('clients.client_label', coach_language_code, client_name=result.client_display_name or t('clients.without_name', coach_language_code))}\n"
                f"{t('meal_reports.meal_type_label', coach_language_code, meal_type_label=meal_type_label)}\n\n"
                f"{t('meal_reports.coach_notification_body', coach_language_code)}"
            ),
        )


@router.message(MealReportStates.waiting_for_photo)
async def process_wrong_meal_photo_handler(message: Message) -> None:
    language_code = await get_user_language(message.from_user.id)
    await message.answer(
        f"{t('meal_reports.photo_only', language_code)}\n\n{t('common.cancel', language_code)} /cancel",
        reply_markup=cancel_keyboard(language_code),
    )

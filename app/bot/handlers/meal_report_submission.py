from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.meal_report_labels import MEAL_TYPE_LABELS
from app.bot.keyboards.meal_reports import meal_type_keyboard
from app.bot.states.meal_reports import MealReportStates
from app.bot.utils.safe_messages import safe_edit_text
from app.services.meal_reports import create_meal_report_from_photo
from app.services.notifications import send_logged_message

router = Router()


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

    await safe_edit_text(
        callback.message,
        text="Прием пищи выбран: "
        f"{MEAL_TYPE_LABELS[meal_type]}\n\n"
        "Теперь отправьте фото еды.\n"
        "Можно добавить подпись к фото, если хотите.",
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

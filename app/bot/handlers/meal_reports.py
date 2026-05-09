from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.meal_reports import (
    meal_review_keyboard,
    meal_type_keyboard,
    pending_meal_reports_keyboard,
)
from app.bot.states.meal_reports import MealReportStates
from app.services.meal_reports import (
    create_meal_report_from_photo,
    get_meal_report_for_coach,
    list_pending_meal_reports_for_coach,
    review_meal_report,
)

router = Router()


MEAL_TYPE_LABELS = {
    "breakfast": "Завтрак",
    "lunch": "Обед",
    "dinner": "Ужин",
    "snack": "Перекус",
    "other": "Другое",
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

    await callback.message.edit_text(
        "Прием пищи выбран: "
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
        try:
            meal_type_label = MEAL_TYPE_LABELS.get(
                result.meal_type or "",
                result.meal_type or "не указан",
            )

            await message.bot.send_message(
                chat_id=result.coach_telegram_id,
                text=(
                    "Новый отчет еды.\n\n"
                    f"Клиент: {result.client_display_name or 'без имени'}\n"
                    f"Прием пищи: {meal_type_label}\n\n"
                    "Откройте раздел “🍽 Отчеты еды”, чтобы проверить отчет."
                ),
            )
        except Exception:
            # Клиентский flow не ломаем, если уведомление тренеру не ушло.
            # Позже лучше логировать это в notification_logs.
            pass


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
async def pending_meal_reports_handler(message: Message) -> None:
    reports = await list_pending_meal_reports_for_coach(
        telegram_id=message.from_user.id,
        limit=10,
    )

    if not reports:
        await message.answer("Нет отчетов еды на проверку.")
        return

    await message.answer(
        "Отчеты еды на проверку:",
        reply_markup=pending_meal_reports_keyboard(reports),
    )


@router.callback_query(F.data == "mr:list")
async def pending_meal_reports_callback_handler(callback: CallbackQuery) -> None:
    reports = await list_pending_meal_reports_for_coach(
        telegram_id=callback.from_user.id,
        limit=10,
    )

    await callback.answer()

    if not reports:
        await callback.message.edit_text("Нет отчетов еды на проверку.")
        return

    await callback.message.edit_text(
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
        await callback.message.edit_text(
            "Отчет не найден или у вас нет доступа."
        )
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
        await callback.message.edit_text(
            "У отчета нет доступного Telegram file_id."
        )
        return

    await callback.message.edit_text(
        "Открываю отчет..."
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
async def review_meal_report_needs_improvement_handler(callback: CallbackQuery) -> None:
    report_id = callback.data.split(":", 2)[2]
    await process_meal_report_review(callback, report_id, "needs_improvement")


@router.callback_query(F.data.startswith("mr:q:"))
async def review_meal_report_question_handler(callback: CallbackQuery) -> None:
    report_id = callback.data.split(":", 2)[2]
    await process_meal_report_review(callback, report_id, "question")


async def process_meal_report_review(
    callback: CallbackQuery,
    report_id: str,
    verdict: str,
) -> None:
    result = await review_meal_report(
        telegram_id=callback.from_user.id,
        report_id=report_id,
        verdict=verdict,
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
        try:
            await callback.bot.send_message(
                chat_id=result.client_telegram_id,
                text=(
                    "Тренер проверил ваш отчет еды.\n\n"
                    f"Результат: {verdict_label}"
                ),
            )
        except Exception:
            pass
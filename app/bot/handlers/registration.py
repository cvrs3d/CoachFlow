from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.privacy import privacy_consent_keyboard
from app.bot.states.registration import RegistrationStates
from app.services.users import set_client_display_name

router = Router()


@router.message(RegistrationStates.waiting_for_display_name)
async def process_display_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    display_name = (message.text or "").strip()

    if len(display_name) < 2:
        await message.answer("Имя слишком короткое. Введите минимум 2 символа.")
        return

    if len(display_name) > 80:
        await message.answer("Имя слишком длинное. Введите до 80 символов.")
        return

    ok = await set_client_display_name(
        telegram_id=message.from_user.id,
        display_name=display_name,
    )

    if not ok:
        await state.clear()
        await message.answer(
            "Не удалось сохранить имя. Попросите тренера отправить новую ссылку."
        )
        return

    await state.clear()

    await message.answer(
        "Имя сохранено.\n\n"
        "Для завершения регистрации нужно согласие на обработку данных.\n\n"
        "Нажимая “Согласен”, вы соглашаетесь, что бот будет хранить:\n\n"
        "- ваш Telegram ID;\n"
        "- имя, указанное для тренера;\n"
        "- ваши записи к тренеру;\n"
        "- историю отмен и статусы записей.\n\n"
        "Данные используются только для организации тренировок.",
        reply_markup=privacy_consent_keyboard(),
    )
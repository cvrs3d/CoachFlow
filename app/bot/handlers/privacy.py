from aiogram import Router, F
from aiogram.types import CallbackQuery

from app.services.users import activate_user_after_consent

from app.bot.keyboards.main_menu import client_main_menu

router = Router()


@router.callback_query(F.data == "privacy:accept")
async def accept_privacy_handler(callback: CallbackQuery) -> None:
    ok = await activate_user_after_consent(callback.from_user.id)

    await callback.answer()

    if not ok:
        await callback.message.answer(
            "Не удалось активировать профиль. Попросите тренера отправить новую ссылку."
        )
        return

    await callback.message.edit_text(
        "Регистрация завершена.\n\n"
        "Теперь вы можете пользоваться ботом."
    )

    await callback.message.answer(
        "Главное меню клиента:",
        reply_markup=client_main_menu(),
    )


@router.callback_query(F.data == "privacy:decline")
async def decline_privacy_handler(callback: CallbackQuery) -> None:
    await callback.answer()

    await callback.message.edit_text(
        "Регистрация не завершена.\n\n"
        "Без согласия на обработку данных бот не может использоваться."
    )
from aiogram.fsm.state import State, StatesGroup


class ClientEditStates(StatesGroup):
    waiting_for_new_display_name = State()
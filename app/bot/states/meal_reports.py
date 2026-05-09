from aiogram.fsm.state import State, StatesGroup


class MealReportStates(StatesGroup):
    waiting_for_photo = State()
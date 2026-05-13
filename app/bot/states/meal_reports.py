from aiogram.fsm.state import State, StatesGroup


class MealReportStates(StatesGroup):
    waiting_for_photo = State()
    waiting_for_review_comment = State()
    waiting_for_clarification_response = State()

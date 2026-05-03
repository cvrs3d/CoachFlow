from aiogram.fsm.state import State, StatesGroup


class ScheduleStates(StatesGroup):
    waiting_for_slot_date = State()
    waiting_for_slot_start_time = State()
    waiting_for_slot_duration = State()
from aiogram.filters.callback_data import CallbackData


# coach_dashboard
# coach_invite
# coach_schedule
# coach_clients
# coach_meal_reports
# coach_meal_schedule
# client_booking
# client_bookings
# client_meal_submit
# client_meal_reports
# client_profile
# language
class MainMenuCallback(CallbackData, prefix="menu"):
    action: str
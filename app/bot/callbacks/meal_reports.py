from aiogram.filters.callback_data import CallbackData


class MealTypeCallback(CallbackData, prefix="mr_t"):
    meal_type: str


class CoachMealReportFilterCallback(CallbackData, prefix="mr_f"):
    report_filter: str


class OpenCoachMealReportCallback(CallbackData, prefix="mr_o"):
    report_id: str


class ReviewMealReportCallback(CallbackData, prefix="mr_r"):
    action: str
    report_id: str


class ClientMealReportFilterCallback(CallbackData, prefix="mr_cf"):
    report_filter: str


class OpenClientMealReportCallback(CallbackData, prefix="mr_co"):
    report_id: str


class ReplyMealReportCallback(CallbackData, prefix="mr_reply"):
    report_id: str

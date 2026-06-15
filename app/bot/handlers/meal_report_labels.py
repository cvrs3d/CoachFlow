from app.bot.i18n import t


def get_meal_type_label(meal_type: str, language_code: str) -> str:
    return t(f"meal_type.{meal_type}", language_code)


def get_report_status_label(status: str, language_code: str) -> str:
    return t(f"report_status.{status}", language_code)


def get_verdict_label(verdict: str, language_code: str) -> str:
    return t(f"verdict.{verdict}", language_code)


def get_coach_report_filter_label(report_filter: str, language_code: str) -> str:
    return t(f"coach_report_filter.{report_filter}", language_code)


def get_client_report_filter_label(report_filter: str, language_code: str) -> str:
    return t(f"client_report_filter.{report_filter}", language_code)

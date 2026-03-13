from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

MONTHS = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

SHORT_MONTHS = {
    1: "янв",
    2: "фев",
    3: "мар",
    4: "апр",
    5: "мая",
    6: "июн",
    7: "июл",
    8: "авг",
    9: "сен",
    10: "окт",
    11: "ноя",
    12: "дек",
}

WEEKDAYS = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}


def get_upcoming_dates(days: int, timezone: ZoneInfo | None = None) -> list[date]:
    today = datetime.now(timezone).date() if timezone else datetime.now().date()
    return [today + timedelta(days=offset) for offset in range(days)]


def format_date_button(day: date) -> str:
    today = datetime.now().date()
    if day == today:
        prefix = "Сегодня"
    elif day == today + timedelta(days=1):
        prefix = "Завтра"
    else:
        prefix = WEEKDAYS[day.weekday()]

    return f"{prefix} · {day.day} {SHORT_MONTHS[day.month]}"


def format_full_datetime(iso_date: str, time_value: str) -> str:
    return f"{format_full_date(iso_date)}, {time_value}"


def format_short_date(iso_date: str) -> str:
    day = date.fromisoformat(iso_date)
    return f"{day.day} {SHORT_MONTHS[day.month]}"


def format_full_date(iso_date: str) -> str:
    day = date.fromisoformat(iso_date)
    return f"{day.day} {MONTHS[day.month]} {day.year}"


def combine_date_time(iso_date: str, time_value: str, timezone: str) -> datetime:
    naive_value = datetime.fromisoformat(f"{iso_date}T{time_value}:00")
    return naive_value.replace(tzinfo=ZoneInfo(timezone))

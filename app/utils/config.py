import os
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


@dataclass(slots=True)
class Settings:
    bot_token: str
    admin_chat_id: int | None
    database_path: Path
    services_path: Path
    studio_name: str
    studio_phone: str
    studio_address: str
    studio_hours: str
    timezone: str
    reminder_hours_before: int
    booking_window_days: int
    time_slots: tuple[str, ...]
    zoneinfo: ZoneInfo


def load_settings() -> Settings:
    load_dotenv()
    base_dir = Path(__file__).resolve().parents[2]

    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required in .env")

    admin_chat_id_raw = os.getenv("ADMIN_CHAT_ID", "").strip()
    timezone = os.getenv("TIMEZONE", "Europe/Moscow")

    return Settings(
        bot_token=bot_token,
        admin_chat_id=int(admin_chat_id_raw) if admin_chat_id_raw else None,
        database_path=base_dir / os.getenv("DATABASE_PATH", "data/bookings.db"),
        services_path=base_dir / os.getenv("SERVICES_PATH", "data/services.json"),
        studio_name=os.getenv("STUDIO_NAME", "Linea Beauty Studio"),
        studio_phone=os.getenv("STUDIO_PHONE", "+7 (999) 123-45-67"),
        studio_address=os.getenv("STUDIO_ADDRESS", "ул. Радищева, 18, 2 этаж"),
        studio_hours=os.getenv("STUDIO_HOURS", "Ежедневно, 10:00-21:00"),
        timezone=timezone,
        reminder_hours_before=int(os.getenv("REMINDER_HOURS_BEFORE", "2")),
        booking_window_days=int(os.getenv("BOOKING_WINDOW_DAYS", "7")),
        time_slots=tuple(
            slot.strip()
            for slot in os.getenv(
                "TIME_SLOTS",
                "10:00,11:30,13:00,15:00,17:00,19:00",
            ).split(",")
            if slot.strip()
        ),
        zoneinfo=ZoneInfo(timezone),
    )

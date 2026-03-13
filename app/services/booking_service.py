import logging
import re
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

from aiogram import Bot
from aiogram.types import User

from app.database.repository import BookingRepository
from app.services.catalog_service import CatalogService, ServiceItem
from app.utils.config import Settings
from app.utils.dates import combine_date_time, format_full_date, format_full_datetime

logger = logging.getLogger(__name__)

STATUS_LABELS = {
    "confirmed": "Подтверждена",
    "cancelled": "Отменена",
    "completed": "Завершена",
}


class SlotUnavailableError(Exception):
    pass


class BookingService:
    def __init__(
        self,
        repository: BookingRepository,
        catalog_service: CatalogService,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.catalog_service = catalog_service
        self.settings = settings

    def get_available_dates(self):
        from app.utils.dates import get_upcoming_dates

        dates = []
        candidates = get_upcoming_dates(
            self.settings.booking_window_days + 3,
            self.settings.zoneinfo,
        )
        today = datetime.now(self.settings.zoneinfo).date()
        for day in candidates:
            available_slots = self.get_available_slots(day.isoformat())
            minimum_slots = 3 if day == today else 4
            if len(available_slots) >= minimum_slots:
                dates.append(day)
            if len(dates) == self.settings.booking_window_days:
                break
        return dates

    def get_available_slots(self, booking_date: str) -> list[str]:
        busy_slots = self.repository.get_busy_slots(booking_date)
        unavailable_slots = busy_slots | self._get_past_slots(booking_date) | self._get_demo_busy_slots(booking_date)
        return [slot for slot in self.settings.time_slots if slot not in unavailable_slots]

    def validate_client_name(self, raw_name: str) -> str | None:
        normalized = " ".join(raw_name.strip().split())
        if not 2 <= len(normalized) <= 40:
            return None
        if not re.fullmatch(r"[A-Za-zА-Яа-яЁё\s\-]+", normalized):
            return None
        return normalized

    def validate_and_normalize_phone(self, raw_phone: str) -> str | None:
        digits = re.sub(r"\D", "", raw_phone)
        if len(digits) == 10:
            digits = "7" + digits
        elif len(digits) == 11 and digits.startswith("8"):
            digits = "7" + digits[1:]

        if len(digits) != 11 or not digits.startswith("7"):
            return None

        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"

    def build_draft_summary(self, draft: dict[str, Any]) -> str:
        service = self.catalog_service.get_service(draft["service_id"])
        if service is None:
            return "Выберите услугу заново."

        return self._build_summary_from_parts(
            service=service,
            booking_date=draft["booking_date"],
            booking_time=draft["booking_time"],
        )

    def build_confirmation_details(self, draft: dict[str, Any], phone: str) -> str:
        service = self.catalog_service.get_service(draft["service_id"])
        if service is None:
            return "Запись нужно начать заново."

        return (
            f"{self._build_summary_from_parts(service, draft['booking_date'], draft['booking_time'])}\n"
            f"<b>Имя:</b> {draft['full_name']}\n"
            f"<b>Телефон:</b> {phone}"
        )

    def build_booking_card(self, booking: dict[str, Any]) -> str:
        return (
            f"<b>Услуга:</b> {booking['service_title']}\n"
            f"<b>Дата:</b> {format_full_date(booking['booking_date'])}\n"
            f"<b>Время:</b> {booking['booking_time']}\n"
            f"<b>Продолжительность:</b> {booking['service_duration']} мин\n"
            f"<b>Стоимость:</b> {self._format_price(booking['service_price'])}\n"
            f"<b>Статус:</b> {self.status_label(booking['status'])}"
        )

    def build_bookings_overview(self, bookings: list[dict[str, Any]]) -> str:
        lines = ["<b>Мои записи</b>", "Ближайшие и прошедшие визиты.", ""]
        for booking in bookings:
            lines.append(
                f"<b>{format_full_datetime(booking['booking_date'], booking['booking_time'])}</b>\n"
                f"{booking['service_title']} · {self.status_label(booking['status'])}"
            )
        lines.append("Откройте запись, чтобы посмотреть детали.")
        return "\n".join(lines)

    def build_record_details(self, booking: dict[str, Any]) -> str:
        return (
            f"{self.build_booking_card(booking)}\n"
            f"<b>Имя:</b> {booking['full_name']}\n"
            f"<b>Телефон:</b> {booking['phone']}"
        )

    def build_reminder_text(self, booking: dict[str, Any]) -> str:
        return (
            "<b>Напоминание о визите</b>\n\n"
            f"{self.build_booking_card(booking)}\n\n"
            f"Если планы изменились, запись можно отменить в разделе «Мои записи»."
        )

    def get_user_bookings(self, user_id: int) -> list[dict[str, Any]]:
        return self.repository.list_user_bookings(user_id)

    def get_user_booking(self, booking_id: int, user_id: int) -> dict[str, Any] | None:
        return self.repository.get_user_booking(booking_id, user_id)

    def cancel_booking(self, booking_id: int, user_id: int) -> dict[str, Any] | None:
        now_iso = datetime.now(self.settings.zoneinfo).isoformat()
        return self.repository.cancel_booking(booking_id, user_id, now_iso)

    def create_booking(self, user: User, chat_id: int, draft: dict[str, Any]) -> dict[str, Any]:
        service = self.catalog_service.get_service(draft["service_id"])
        if service is None:
            raise SlotUnavailableError("Selected service does not exist.")
        if draft["booking_time"] not in self.get_available_slots(draft["booking_date"]):
            raise SlotUnavailableError("Selected slot is unavailable.")

        appointment_at = combine_date_time(
            draft["booking_date"],
            draft["booking_time"],
            self.settings.timezone,
        )
        payload = {
            "user_id": user.id,
            "chat_id": chat_id,
            "username": user.username,
            "full_name": draft["full_name"],
            "phone": draft["phone"],
            "service_id": service["id"],
            "service_title": service["title"],
            "service_price": service["price"],
            "service_duration": service["duration_min"],
            "booking_date": draft["booking_date"],
            "booking_time": draft["booking_time"],
            "appointment_at": appointment_at.isoformat(),
            "status": "confirmed",
            "created_at": datetime.now(self.settings.zoneinfo).isoformat(),
            "updated_at": datetime.now(self.settings.zoneinfo).isoformat(),
        }

        try:
            return self.repository.create_booking(payload)
        except sqlite3.IntegrityError as error:
            raise SlotUnavailableError from error

    async def notify_admin_about_new_booking(
        self,
        bot: Bot,
        booking: dict[str, Any],
        user: User,
    ) -> None:
        if self.settings.admin_chat_id is None:
            return

        text = (
            "<b>Новая запись</b>\n\n"
            f"{self.build_booking_card(booking)}\n"
            f"<b>Имя:</b> {booking['full_name']}\n"
            f"<b>Телефон:</b> {booking['phone']}\n"
            f"<b>Telegram:</b> {self._format_user_link(user)}"
        )
        await self._safe_send_admin_message(bot, text)

    async def notify_admin_about_cancelled_booking(
        self,
        bot: Bot,
        booking: dict[str, Any],
        user: User,
    ) -> None:
        if self.settings.admin_chat_id is None:
            return

        text = (
            "<b>Отмена записи</b>\n\n"
            f"{self.build_booking_card(booking)}\n"
            f"<b>Имя:</b> {booking['full_name']}\n"
            f"<b>Телефон:</b> {booking['phone']}\n"
            f"<b>Telegram:</b> {self._format_user_link(user)}"
        )
        await self._safe_send_admin_message(bot, text)

    def status_label(self, status: str) -> str:
        return STATUS_LABELS.get(status, status)

    def _build_summary_from_parts(
        self,
        service: ServiceItem,
        booking_date: str,
        booking_time: str,
    ) -> str:
        return (
            f"<b>Услуга:</b> {service['title']}\n"
            f"<b>Дата:</b> {format_full_date(booking_date)}\n"
            f"<b>Время:</b> {booking_time}\n"
            f"<b>Продолжительность:</b> {service['duration_min']} мин\n"
            f"<b>Стоимость:</b> {self._format_price(service['price'])}"
        )

    async def _safe_send_admin_message(self, bot: Bot, text: str) -> None:
        try:
            await bot.send_message(self.settings.admin_chat_id, text)
        except Exception:
            logger.exception("Failed to send admin notification")

    def _format_price(self, value: int) -> str:
        return f"{value:,}".replace(",", " ") + " ₽"

    def _format_user_link(self, user: User) -> str:
        if user.username:
            return f"@{user.username}"
        return f"ID {user.id}"

    def _get_past_slots(self, booking_date: str) -> set[str]:
        today = datetime.now(self.settings.zoneinfo)
        if booking_date != today.date().isoformat():
            return set()

        threshold = (today + timedelta(minutes=30)).time()
        return {slot for slot in self.settings.time_slots if self._parse_time(slot) <= threshold}

    def _get_demo_busy_slots(self, booking_date: str) -> set[str]:
        day = date.fromisoformat(booking_date)
        if day == datetime.now(self.settings.zoneinfo).date():
            return set()
        if len(self.settings.time_slots) <= 4:
            return set()

        seed = day.toordinal()
        blocked_slots = {self.settings.time_slots[-1]}
        if seed % 3 == 0 and len(self.settings.time_slots) >= 6:
            blocked_slots.add(self.settings.time_slots[-2])
        return blocked_slots

    def _parse_time(self, value: str):
        return datetime.strptime(value, "%H:%M").time()

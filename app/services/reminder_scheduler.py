import logging
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from app.keyboards.main_menu import main_menu_keyboard
from app.services.booking_service import BookingService
from app.utils.config import Settings

logger = logging.getLogger(__name__)


class ReminderScheduler:
    def __init__(
        self,
        bot: Bot,
        booking_service: BookingService,
        settings: Settings,
    ) -> None:
        self.bot = bot
        self.booking_service = booking_service
        self.settings = settings
        self.scheduler = AsyncIOScheduler(timezone=settings.timezone)

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    async def restore_pending_reminders(self) -> None:
        now_iso = datetime.now(self.settings.zoneinfo).isoformat()
        for booking in self.booking_service.repository.list_future_confirmed_bookings(now_iso):
            await self.schedule_booking_reminder(booking)

    async def schedule_booking_reminder(self, booking: dict) -> None:
        appointment_at = datetime.fromisoformat(booking["appointment_at"])
        run_at = appointment_at - timedelta(hours=self.settings.reminder_hours_before)
        now = datetime.now(self.settings.zoneinfo)
        if run_at <= now:
            return

        self.scheduler.add_job(
            self._send_reminder,
            trigger=DateTrigger(run_date=run_at),
            id=self._job_id(booking["id"]),
            replace_existing=True,
            kwargs={"booking_id": booking["id"]},
        )

    def remove_booking_reminder(self, booking_id: int) -> None:
        job = self.scheduler.get_job(self._job_id(booking_id))
        if job:
            job.remove()

    async def _send_reminder(self, booking_id: int) -> None:
        booking = self.booking_service.repository.get_booking_by_id(booking_id)
        if booking is None or booking["status"] != "confirmed":
            return

        try:
            await self.bot.send_message(
                booking["chat_id"],
                self.booking_service.build_reminder_text(booking),
                reply_markup=main_menu_keyboard(),
            )
        except Exception:
            logger.exception("Failed to send reminder for booking %s", booking_id)

    def _job_id(self, booking_id: int) -> str:
        return f"booking-reminder:{booking_id}"

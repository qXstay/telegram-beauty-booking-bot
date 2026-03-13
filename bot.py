import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from app.database.connection import Database
from app.database.repository import BookingRepository
from app.handlers import get_routers
from app.services.booking_service import BookingService
from app.services.catalog_service import CatalogService
from app.services.reminder_scheduler import ReminderScheduler
from app.utils.config import load_settings


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    settings = load_settings()
    database = Database(settings.database_path)
    database.connect()
    database.init_schema()

    repository = BookingRepository(database)
    catalog_service = CatalogService(settings.services_path)
    booking_service = BookingService(repository, catalog_service, settings)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    for router in get_routers():
        dispatcher.include_router(router)

    reminder_scheduler = ReminderScheduler(
        bot=bot,
        booking_service=booking_service,
        settings=settings,
    )
    reminder_scheduler.start()
    await reminder_scheduler.restore_pending_reminders()

    try:
        await dispatcher.start_polling(
            bot,
            settings=settings,
            catalog_service=catalog_service,
            booking_service=booking_service,
            reminder_scheduler=reminder_scheduler,
        )
    finally:
        reminder_scheduler.shutdown()
        await bot.session.close()
        database.close()


if __name__ == "__main__":
    asyncio.run(main())

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.booking import cancel_confirmation_keyboard, records_keyboard
from app.keyboards.main_menu import MENU_MY_RECORDS
from app.services.booking_service import BookingService
from app.services.reminder_scheduler import ReminderScheduler

router = Router(name="records")


async def send_records_list(
    target: Message | CallbackQuery,
    booking_service: BookingService,
    user_id: int,
) -> None:
    bookings = booking_service.get_user_bookings(user_id)
    if not bookings:
        text = (
            "<b>Мои записи</b>\n"
            "Здесь появятся ваши ближайшие визиты."
        )
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text)
            await target.answer()
            return

        await target.answer(text)
        return

    text = booking_service.build_bookings_overview(bookings)
    markup = records_keyboard(bookings)

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup)
        await target.answer()
        return

    await target.answer(text, reply_markup=markup)


@router.message(StateFilter("*"), F.text == MENU_MY_RECORDS)
async def show_my_records(
    message: Message,
    state: FSMContext,
    booking_service: BookingService,
) -> None:
    await state.clear()
    await send_records_list(message, booking_service, message.from_user.id)


@router.callback_query(F.data == "records:list")
async def show_my_records_callback(
    callback: CallbackQuery,
    booking_service: BookingService,
) -> None:
    await send_records_list(callback, booking_service, callback.from_user.id)


@router.callback_query(F.data.startswith("records:view:"))
async def show_record_details(
    callback: CallbackQuery,
    booking_service: BookingService,
) -> None:
    booking_id = int(callback.data.split(":")[-1])
    booking = booking_service.get_user_booking(booking_id, callback.from_user.id)
    if booking is None:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    await callback.message.edit_text(
        booking_service.build_record_details(booking),
        reply_markup=cancel_confirmation_keyboard(booking),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("records:cancel:"))
async def request_cancel_record(
    callback: CallbackQuery,
    booking_service: BookingService,
) -> None:
    booking_id = int(callback.data.split(":")[-1])
    booking = booking_service.get_user_booking(booking_id, callback.from_user.id)
    if booking is None:
        await callback.answer("Запись не найдена.", show_alert=True)
        return

    await callback.message.edit_text(
        "<b>Отменить запись?</b>\n\n"
        f"{booking_service.build_booking_card(booking)}\n\n"
        "После отмены это время снова станет доступно для записи.",
        reply_markup=cancel_confirmation_keyboard(booking, confirm=True),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("records:cancel-confirm:"))
async def cancel_record(
    callback: CallbackQuery,
    booking_service: BookingService,
    reminder_scheduler: ReminderScheduler,
) -> None:
    booking_id = int(callback.data.split(":")[-1])
    cancelled_booking = booking_service.cancel_booking(booking_id, callback.from_user.id)
    if cancelled_booking is None:
        await callback.answer("Активная запись не найдена.", show_alert=True)
        return

    reminder_scheduler.remove_booking_reminder(booking_id)
    await booking_service.notify_admin_about_cancelled_booking(
        callback.bot,
        cancelled_booking,
        callback.from_user,
    )

    await callback.message.edit_text(
        "<b>Запись отменена</b>\n\n"
        f"{booking_service.build_booking_card(cancelled_booking)}\n\n"
        "Если понадобится, можно выбрать новое время."
    )
    await callback.answer("Запись отменена")


@router.callback_query(F.data == "records:keep")
async def keep_record(callback: CallbackQuery, booking_service: BookingService) -> None:
    await send_records_list(callback, booking_service, callback.from_user.id)

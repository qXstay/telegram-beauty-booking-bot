from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.booking import (
    booking_confirmation_keyboard,
    dates_keyboard,
    services_keyboard,
    times_keyboard,
)
from app.keyboards.main_menu import MENU_BOOK
from app.services.booking_service import BookingService, SlotUnavailableError
from app.services.catalog_service import CatalogService
from app.services.reminder_scheduler import ReminderScheduler
from app.utils.dates import format_full_date
from app.utils.states import BookingStates

router = Router(name="booking")


def build_name_prompt_text(summary: str) -> str:
    return (
        "<b>Детали визита</b>\n\n"
        f"{summary}\n\n"
        "Как к вам обращаться?"
    )


def build_phone_prompt_text(summary: str, full_name: str) -> str:
    return (
        f"{summary}\n"
        f"<b>Имя:</b> {full_name}\n\n"
        "Укажите контактный номер."
    )


async def send_services_step(
    target: Message | CallbackQuery,
    catalog_service: CatalogService,
) -> None:
    text = (
        "<b>Запись в Linea Beauty Studio</b>\n"
        "Выберите услугу."
    )
    markup = services_keyboard(catalog_service.list_services())

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=markup)
        await target.answer()
        return

    await target.answer(text, reply_markup=markup)


async def send_dates_step(
    callback: CallbackQuery,
    booking_service: BookingService,
) -> None:
    await callback.message.edit_text(
        "<b>Выберите дату</b>\n"
        "Ближайшие свободные даты.",
        reply_markup=dates_keyboard(booking_service.get_available_dates()),
    )
    await callback.answer()


async def send_times_step(
    callback: CallbackQuery,
    booking_service: BookingService,
    booking_date: str,
) -> None:
    slots = booking_service.get_available_slots(booking_date)
    if not slots:
        await callback.answer("На эту дату свободных окон не осталось.", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{format_full_date(booking_date)}</b>\n"
        "Свободное время на эту дату.",
        reply_markup=times_keyboard(slots),
    )
    await callback.answer()


@router.message(StateFilter("*"), F.text == MENU_BOOK)
async def start_booking(
    message: Message,
    state: FSMContext,
    catalog_service: CatalogService,
) -> None:
    await state.clear()
    await state.set_state(BookingStates.choosing_service)
    await send_services_step(message, catalog_service)


@router.callback_query(F.data == "booking:cancel")
async def cancel_booking_flow(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Запись можно оформить позже.")
    await callback.answer()


@router.callback_query(F.data == "booking:back:services")
async def back_to_services(
    callback: CallbackQuery,
    state: FSMContext,
    catalog_service: CatalogService,
) -> None:
    await state.set_state(BookingStates.choosing_service)
    await send_services_step(callback, catalog_service)


@router.callback_query(F.data == "booking:back:dates")
async def back_to_dates(
    callback: CallbackQuery,
    state: FSMContext,
    booking_service: BookingService,
) -> None:
    await state.set_state(BookingStates.choosing_date)
    await send_dates_step(callback, booking_service)


@router.callback_query(F.data.startswith("booking:service:"))
async def pick_service(
    callback: CallbackQuery,
    state: FSMContext,
    catalog_service: CatalogService,
    booking_service: BookingService,
) -> None:
    service_id = callback.data.split(":")[-1]
    service = catalog_service.get_service(service_id)
    if service is None:
        await callback.answer("Услуга не найдена.", show_alert=True)
        return

    await state.update_data(service_id=service_id)
    await state.set_state(BookingStates.choosing_date)
    await send_dates_step(callback, booking_service)


@router.callback_query(F.data.startswith("booking:date:"))
async def pick_date(
    callback: CallbackQuery,
    state: FSMContext,
    booking_service: BookingService,
) -> None:
    booking_date = callback.data.split(":")[-1]
    await state.update_data(booking_date=booking_date)
    await state.set_state(BookingStates.choosing_time)
    await send_times_step(callback, booking_service, booking_date)


@router.callback_query(F.data.startswith("booking:time:"))
async def pick_time(
    callback: CallbackQuery,
    state: FSMContext,
    booking_service: BookingService,
) -> None:
    booking_time = callback.data.removeprefix("booking:time:")
    data = await state.get_data()
    booking_date = data.get("booking_date")
    if not booking_date:
        await callback.answer("Сначала выберите дату.", show_alert=True)
        return

    if booking_time not in booking_service.get_available_slots(booking_date):
        await callback.answer("Это окно уже занято. Выберите другое время.", show_alert=True)
        return

    await state.update_data(booking_time=booking_time)
    await state.set_state(BookingStates.entering_name)
    summary = booking_service.build_draft_summary(await state.get_data())
    await callback.message.edit_text(build_name_prompt_text(summary))
    await callback.answer()


@router.message(BookingStates.entering_name)
async def capture_name(message: Message, state: FSMContext, booking_service: BookingService) -> None:
    full_name = booking_service.validate_client_name(message.text or "")
    if full_name is None:
        await message.answer("Укажите имя в понятном формате, например: Анна.")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(BookingStates.entering_phone)
    summary = booking_service.build_draft_summary(await state.get_data())
    await message.answer(build_phone_prompt_text(summary, full_name))


@router.message(BookingStates.entering_phone)
async def capture_phone(message: Message, state: FSMContext, booking_service: BookingService) -> None:
    normalized_phone = booking_service.validate_and_normalize_phone(message.text or "")
    if normalized_phone is None:
        await message.answer("Введите номер в формате +7 999 123-45-67.")
        return

    await state.update_data(phone=normalized_phone)
    await state.set_state(BookingStates.confirming)
    draft = await state.get_data()
    summary = booking_service.build_confirmation_details(draft, normalized_phone)
    await message.answer(
        "<b>Подтвердите запись</b>\n\n"
        f"{summary}",
        reply_markup=booking_confirmation_keyboard(),
    )


@router.callback_query(F.data == "booking:change-slot")
async def change_booking_slot(
    callback: CallbackQuery,
    state: FSMContext,
    booking_service: BookingService,
) -> None:
    await state.set_state(BookingStates.choosing_date)
    await send_dates_step(callback, booking_service)


@router.callback_query(F.data == "booking:confirm")
async def confirm_booking(
    callback: CallbackQuery,
    state: FSMContext,
    booking_service: BookingService,
    reminder_scheduler: ReminderScheduler,
) -> None:
    draft = await state.get_data()
    if not draft:
        await callback.answer("Сессия записи устарела. Начните заново.", show_alert=True)
        return

    try:
        booking = booking_service.create_booking(
            user=callback.from_user,
            chat_id=callback.message.chat.id,
            draft=draft,
        )
    except SlotUnavailableError:
        await state.set_state(BookingStates.choosing_date)
        await callback.message.edit_text(
            "<b>Это время уже занято</b>\n"
            "Выберите другую дату или свободное окно.",
            reply_markup=dates_keyboard(booking_service.get_available_dates()),
        )
        await callback.answer()
        return

    await reminder_scheduler.schedule_booking_reminder(booking)
    await booking_service.notify_admin_about_new_booking(callback.bot, booking, callback.from_user)

    await state.clear()
    await callback.message.edit_text(
        "<b>Запись подтверждена</b>\n\n"
        f"{booking_service.build_booking_card(booking)}\n\n"
        "Напоминание придёт автоматически."
    )
    await callback.answer()

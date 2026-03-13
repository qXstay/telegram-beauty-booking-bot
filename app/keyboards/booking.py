from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.services.catalog_service import ServiceItem
from app.utils.dates import format_date_button, format_short_date


def format_price(price: int) -> str:
    return f"{price:,}".replace(",", " ") + " ₽"


def services_keyboard(services: Sequence[ServiceItem]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.button(
            text=f"{service['title']} • {service['duration_min']} мин • {format_price(service['price'])}",
            callback_data=f"booking:service:{service['id']}",
        )
    builder.button(text="В меню", callback_data="booking:cancel")
    builder.adjust(1)
    return builder.as_markup()


def dates_keyboard(days: Sequence) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for day in days:
        builder.button(
            text=format_date_button(day),
            callback_data=f"booking:date:{day.isoformat()}",
        )
    builder.button(text="К услугам", callback_data="booking:back:services")
    builder.button(text="В меню", callback_data="booking:cancel")
    builder.adjust(2, 2, 2, 1, 1)
    return builder.as_markup()


def times_keyboard(slots: Sequence[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for slot in slots:
        builder.button(text=slot, callback_data=f"booking:time:{slot}")
    builder.button(text="К датам", callback_data="booking:back:dates")
    builder.button(text="В меню", callback_data="booking:cancel")
    builder.adjust(3, 3, 1, 1)
    return builder.as_markup()


def booking_confirmation_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Подтвердить запись", callback_data="booking:confirm")
    builder.button(text="Выбрать другое время", callback_data="booking:change-slot")
    builder.button(text="Отменить", callback_data="booking:cancel")
    builder.adjust(1)
    return builder.as_markup()


def records_keyboard(bookings: Sequence[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for booking in bookings:
        builder.button(
            text=f"{format_short_date(booking['booking_date'])} • {booking['booking_time']}",
            callback_data=f"records:view:{booking['id']}",
        )
    builder.adjust(1)
    return builder.as_markup()


def cancel_confirmation_keyboard(
    booking: dict,
    confirm: bool = False,
) -> InlineKeyboardMarkup:
    if confirm:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Отменить запись",
                        callback_data=f"records:cancel-confirm:{booking['id']}",
                    )
                ],
                [InlineKeyboardButton(text="Оставить как есть", callback_data="records:keep")],
            ]
        )

    inline_keyboard = []
    if booking["status"] == "confirmed":
        inline_keyboard.append(
            [InlineKeyboardButton(text="Отменить визит", callback_data=f"records:cancel:{booking['id']}")]
        )
    inline_keyboard.append([InlineKeyboardButton(text="К списку", callback_data="records:list")])
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MENU_BOOK = "Записаться"
MENU_MY_RECORDS = "Мои записи"
MENU_CONTACTS = "Контакты"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_BOOK)],
            [KeyboardButton(text=MENU_MY_RECORDS), KeyboardButton(text=MENU_CONTACTS)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите раздел",
    )

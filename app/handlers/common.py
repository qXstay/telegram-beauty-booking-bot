from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.main_menu import MENU_CONTACTS, main_menu_keyboard
from app.utils.config import Settings

router = Router(name="common")


def build_welcome_text(settings: Settings) -> str:
    return (
        f"<b>{settings.studio_name}</b>\n"
        "Онлайн-запись на beauty-услуги.\n\n"
        "Выберите процедуру, удобную дату и время. "
        "Подтверждение и напоминание придут в этот чат."
    )


def build_contacts_text(settings: Settings) -> str:
    return (
        f"<b>{settings.studio_name}</b>\n"
        f"<b>Адрес:</b> {settings.studio_address}\n"
        f"<b>Часы работы:</b> {settings.studio_hours}\n"
        f"<b>Телефон:</b> {settings.studio_phone}\n\n"
        "Если удобного окна нет, напишите нам. Подберём время вручную."
    )


@router.message(CommandStart(), StateFilter("*"))
async def cmd_start(message: Message, state: FSMContext, settings: Settings) -> None:
    await state.clear()
    await message.answer(build_welcome_text(settings), reply_markup=main_menu_keyboard())


@router.message(Command("menu"), StateFilter("*"))
async def cmd_menu(message: Message, state: FSMContext, settings: Settings) -> None:
    await state.clear()
    await message.answer(build_welcome_text(settings), reply_markup=main_menu_keyboard())


@router.message(StateFilter("*"), F.text == MENU_CONTACTS)
async def show_contacts(message: Message, state: FSMContext, settings: Settings) -> None:
    await state.clear()
    await message.answer(build_contacts_text(settings), reply_markup=main_menu_keyboard())

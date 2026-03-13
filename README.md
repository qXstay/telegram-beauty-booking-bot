# Telegram Booking Reminder Bot

Telegram-бот для записи на услуги и автоматических напоминаний.

## Стек
- Python
- aiogram 3
- SQLite
- APScheduler

## Возможности
- выбор услуги
- выбор даты и времени
- подтверждение записи
- уведомление администратору
- напоминание клиенту

## Запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
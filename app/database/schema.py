SCHEMA = """
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    chat_id INTEGER NOT NULL,
    username TEXT,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    service_id TEXT NOT NULL,
    service_title TEXT NOT NULL,
    service_price INTEGER NOT NULL,
    service_duration INTEGER NOT NULL,
    booking_date TEXT NOT NULL,
    booking_time TEXT NOT NULL,
    appointment_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'confirmed',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    cancelled_at TEXT
);

DROP INDEX IF EXISTS idx_bookings_unique_confirmed_slot;

CREATE UNIQUE INDEX IF NOT EXISTS idx_bookings_unique_confirmed_slot_active
ON bookings (booking_date, booking_time)
WHERE status = 'confirmed';

CREATE INDEX IF NOT EXISTS idx_bookings_user_id
ON bookings (user_id);

CREATE INDEX IF NOT EXISTS idx_bookings_appointment_at
ON bookings (appointment_at);
"""

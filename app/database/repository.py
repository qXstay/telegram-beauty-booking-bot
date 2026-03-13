import sqlite3
from collections.abc import Iterable
from typing import Any

from app.database.connection import Database


class BookingRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create_booking(self, payload: dict[str, Any]) -> dict[str, Any]:
        connection = self.database.connect()
        cursor = connection.execute(
            """
            INSERT INTO bookings (
                user_id, chat_id, username, full_name, phone,
                service_id, service_title, service_price, service_duration,
                booking_date, booking_time, appointment_at,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["user_id"],
                payload["chat_id"],
                payload["username"],
                payload["full_name"],
                payload["phone"],
                payload["service_id"],
                payload["service_title"],
                payload["service_price"],
                payload["service_duration"],
                payload["booking_date"],
                payload["booking_time"],
                payload["appointment_at"],
                payload["status"],
                payload["created_at"],
                payload["updated_at"],
            ),
        )
        connection.commit()
        return self.get_booking_by_id(cursor.lastrowid)

    def get_busy_slots(self, booking_date: str) -> set[str]:
        connection = self.database.connect()
        rows = connection.execute(
            """
            SELECT booking_time
            FROM bookings
            WHERE booking_date = ? AND status = 'confirmed'
            """,
            (booking_date,),
        ).fetchall()
        return {row["booking_time"] for row in rows}

    def list_user_bookings(self, user_id: int) -> list[dict[str, Any]]:
        connection = self.database.connect()
        rows = connection.execute(
            """
            SELECT *
            FROM bookings
            WHERE user_id = ?
            ORDER BY
                CASE status
                    WHEN 'confirmed' THEN 0
                    WHEN 'completed' THEN 1
                    ELSE 2
                END,
                appointment_at ASC
            """,
            (user_id,),
        ).fetchall()
        return self._rows_to_dicts(rows)

    def get_user_booking(self, booking_id: int, user_id: int) -> dict[str, Any] | None:
        connection = self.database.connect()
        row = connection.execute(
            """
            SELECT *
            FROM bookings
            WHERE id = ? AND user_id = ?
            """,
            (booking_id, user_id),
        ).fetchone()
        return dict(row) if row else None

    def get_booking_by_id(self, booking_id: int) -> dict[str, Any] | None:
        connection = self.database.connect()
        row = connection.execute(
            """
            SELECT *
            FROM bookings
            WHERE id = ?
            """,
            (booking_id,),
        ).fetchone()
        return dict(row) if row else None

    def cancel_booking(self, booking_id: int, user_id: int, now_iso: str) -> dict[str, Any] | None:
        connection = self.database.connect()
        cursor = connection.execute(
            """
            UPDATE bookings
            SET status = 'cancelled', cancelled_at = ?, updated_at = ?
            WHERE id = ? AND user_id = ? AND status = 'confirmed'
            """,
            (now_iso, now_iso, booking_id, user_id),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return None
        return self.get_booking_by_id(booking_id)

    def list_future_confirmed_bookings(self, now_iso: str) -> list[dict[str, Any]]:
        connection = self.database.connect()
        rows = connection.execute(
            """
            SELECT *
            FROM bookings
            WHERE status = 'confirmed' AND appointment_at > ?
            ORDER BY appointment_at ASC
            """,
            (now_iso,),
        ).fetchall()
        return self._rows_to_dicts(rows)

    def _rows_to_dicts(self, rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
        return [dict(row) for row in rows]

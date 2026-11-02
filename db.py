"""Bookings stored in SQLite."""
import os
import sqlite3
from pathlib import Path

DB_PATH = os.environ.get("BOOKINGS_DB", Path(__file__).parent / "bookings.db")
_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.execute("""CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER, name TEXT, phone TEXT,
    service TEXT, day TEXT, time TEXT,
    UNIQUE(day, time))""")
_conn.commit()


def taken(day: str) -> set[str]:
    return {r[0] for r in _conn.execute("SELECT time FROM bookings WHERE day=?", (day,))}


def add(user_id, name, phone, service, day, time) -> bool:
    """False if someone has just taken this slot."""
    try:
        _conn.execute("INSERT INTO bookings (user_id,name,phone,service,day,time) VALUES (?,?,?,?,?,?)",
                      (user_id, name, phone, service, day, time))
        _conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def of_user(user_id, from_day: str):
    return _conn.execute("SELECT id, service, day, time FROM bookings WHERE user_id=? AND day>=? "
                         "ORDER BY day, time", (user_id, from_day)).fetchall()


def on_day(day: str):
    return _conn.execute("SELECT time, name, phone, service FROM bookings WHERE day=? ORDER BY time",
                         (day,)).fetchall()


def cancel(booking_id: int, user_id: int):
    row = _conn.execute("SELECT service, day, time FROM bookings WHERE id=? AND user_id=?",
                        (booking_id, user_id)).fetchone()
    if row:
        _conn.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
        _conn.commit()
    return row

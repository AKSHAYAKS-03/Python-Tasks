import os
import sqlite3
from datetime import datetime

# Database file path
DB_PATH = os.path.join("data", "chat.db")


def get_connection():
    # Create data folder if it does not exist
    os.makedirs("data", exist_ok=True)

    # Connect to SQLite database
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_connection()
    cursor = connection.cursor()

    # Table to store users and their status
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'offline',
            last_seen TEXT
        )
    """)

    # Table to store messages
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT,
            room TEXT,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            type TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


def save_user(username, status="offline"):
    connection = get_connection()
    cursor = connection.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Insert user if new, update if already exists
    cursor.execute("""
        INSERT INTO users (username, status, last_seen)
        VALUES (?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            status = excluded.status,
            last_seen = excluded.last_seen
    """, (username, status, now))

    connection.commit()
    connection.close()


def update_user_status(username, status):
    connection = get_connection()
    cursor = connection.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        UPDATE users
        SET status = ?, last_seen = ?
        WHERE username = ?
    """, (status, now, username))

    connection.commit()
    connection.close()


def save_message(sender, receiver, room, message, message_type):
    connection = get_connection()
    cursor = connection.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO messages (sender, receiver, room, message, timestamp, type)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (sender, receiver, room, message, timestamp, message_type))

    connection.commit()
    connection.close()
    return timestamp


def get_room_history(room, limit=20):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT sender, message, timestamp, type
        FROM messages
        WHERE room = ? AND type = 'room'
        ORDER BY id DESC
        LIMIT ?
    """, (room, limit))

    rows = cursor.fetchall()
    connection.close()

    history = [dict(row) for row in rows]
    history.reverse()   # old to new
    return history


def search_messages(keyword="", room=""):
    connection = get_connection()
    cursor = connection.cursor()

    query = """
        SELECT sender, receiver, room, message, timestamp, type
        FROM messages
        WHERE message LIKE ?
    """
    values = [f"%{keyword}%"]

    if room:
        query += " AND room = ?"
        values.append(room)

    query += " ORDER BY id DESC LIMIT 20"

    cursor.execute(query, values)
    rows = cursor.fetchall()
    connection.close()

    return [dict(row) for row in rows]
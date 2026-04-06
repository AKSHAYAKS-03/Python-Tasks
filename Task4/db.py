
import sqlite3

DB_NAME = "results.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_results (
            task_id TEXT PRIMARY KEY,
            func_name TEXT,
            status TEXT,
            retries INTEGER,
            duration REAL,
            result TEXT,
            error TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_result(task_id, func_name, status, retries, duration, result, error):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR REPLACE INTO task_results
        (task_id, func_name, status, retries, duration, result, error)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (task_id, func_name, status, retries, duration, result, error))

    conn.commit()

    conn.close()



def fetch_all_results():
    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM task_results")

    rows = cursor.fetchall()

    conn.close()

    return rows
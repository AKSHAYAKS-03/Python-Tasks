import sqlite3
from datetime import datetime

DB_NAME = "products.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scrape_date TEXT,
            name TEXT,
            price REAL,
            sku TEXT UNIQUE
        )
    """)

    conn.commit()
    conn.close()

def save_products(products):
    conn = get_connection()
    cursor = conn.cursor()

    today = datetime.now().strftime("%Y-%m-%d")

    for product in products:
        cursor.execute("""
            INSERT INTO products (scrape_date, name, price, sku)
            VALUES (?, ?, ?, ?)
        """, (today, product["name"], product["price"], product["sku"]))

    conn.commit()
    conn.close()

def get_previous_price(sku, current_scrape_time):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT price FROM products
        WHERE sku = ? AND scrape_date < ?
        ORDER BY scrape_date DESC
        LIMIT 1
    """, (sku, current_scrape_time))

    row = cursor.fetchone()
    conn.close()

    if row:
        return row[0]
    return None
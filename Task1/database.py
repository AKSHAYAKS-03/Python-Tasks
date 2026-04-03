import sqlite3
from datetime import date, datetime


def init_db(db_path: str = "products.db"):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            product_url TEXT,
            scraped_date TEXT NOT NULL,
            scraped_at TEXT NOT NULL,
            UNIQUE(sku, scraped_date)
        )
        """
    )
    ensure_column(conn, "products", "product_url", "TEXT")
    ensure_column(conn, "products", "scraped_at", "TEXT")
    conn.commit()
    return conn


def ensure_column(conn, table_name: str, column_name: str, column_type: str) -> None:
    columns = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in columns:
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        )


def save_products(conn, products: list[dict], scrape_date: str | None = None):
    scrape_date = scrape_date or str(date.today())
    scraped_at = datetime.now().isoformat(timespec="seconds")

    rows = [
        (
            product["sku"],
            product["name"],
            product["price"],
            product.get("url"),
            scrape_date,
            scraped_at,
        )
        for product in products
    ]

    conn.executemany(
        """
        INSERT OR REPLACE INTO products
        (sku, name, price, product_url, scraped_date, scraped_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    print(f"Saved {len(rows)} products to DB")


def get_snapshot_dates(conn) -> list[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT scraped_date
        FROM products
        ORDER BY scraped_date DESC
        """
    ).fetchall()
    return [row[0] for row in rows]

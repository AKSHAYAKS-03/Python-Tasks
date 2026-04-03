import csv
import os
from datetime import date, timedelta


def detect_price_changes(conn):
    current_date = str(date.today())
    previous_date = str(date.today() - timedelta(days=1))
    current_exists = conn.execute(
        "SELECT 1 FROM products WHERE scraped_date = ? LIMIT 1",
        (current_date,),
    ).fetchone()
    previous_exists = conn.execute(
        "SELECT 1 FROM products WHERE scraped_date = ? LIMIT 1",
        (previous_date,),
    ).fetchone()

    if not current_exists or not previous_exists:
        return [], current_date, previous_date

    cursor = conn.execute(
        """
        SELECT
            current.name,
            previous.price AS old_price,
            current.price AS new_price,
            ROUND(((current.price - previous.price) / previous.price) * 100, 1) AS change_pct
        FROM products current
        JOIN products previous
          ON current.sku = previous.sku
        WHERE current.scraped_date = ?
          AND previous.scraped_date = ?
          AND current.price != previous.price
        ORDER BY ABS(change_pct) DESC, current.name ASC
        """,
        (current_date, previous_date),
    )
    return cursor.fetchall(), current_date, previous_date


def export_report(changes, report_date: str | None = None):
    report_date = report_date or str(date.today())
    os.makedirs("reports", exist_ok=True)
    filename = os.path.join("reports", f"{report_date}.csv")

    with open(filename, "w", newline="", encoding="utf-8") as report_file:
        writer = csv.writer(report_file)
        writer.writerow(["Product", "Old Price", "New Price", "Change %"])

        for product, old_price, new_price, change_pct in changes:
            writer.writerow(
                [
                    product,
                    f"{old_price:.2f}",
                    f"{new_price:.2f}",
                    f"{change_pct:+.1f}%",
                ]
            )

    return filename


def print_price_change_report(changes, previous_date: str, current_date: str) -> None:
    if not changes:
        print("No price changes detected.")
        return

    print("\n=== Price Change Report ===")
    print(f"Comparing {previous_date} -> {current_date}")
    print("+-------------------------------+-----------+-----------+--------+")
    print("| Product                       | Old Price | New Price | Change |")
    print("+-------------------------------+-----------+-----------+--------+")

    for product, old_price, new_price, change_pct in changes:
        name = truncate(product, 29)
        print(
            f"| {name:<29} | ${old_price:>8.2f} | ${new_price:>8.2f} | {change_pct:>+6.1f}% |"
        )

    print("+-------------------------------+-----------+-----------+--------+")
    print(f"{len(changes)} price changes detected.")


def truncate(value: str, length: int) -> str:
    if len(value) <= length:
        return value
    return value[: length - 3] + "..."

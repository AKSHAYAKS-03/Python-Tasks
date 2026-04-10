import csv
import os
from datetime import datetime

from db import get_previous_price

def generate_price_change_report(products):
    today = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    os.makedirs("reports", exist_ok=True)

    report_file = f"reports/{today}.csv"
    changes = []

    for product in products:
        old_price = get_previous_price(product["sku"], today)
        new_price = product["price"]

        if old_price is not None and old_price != new_price:
            percent_change = ((new_price - old_price) / old_price) * 100

            changes.append({
                "name": product["name"],
                "old_price": old_price,
                "new_price": new_price,
                "change_percent": round(percent_change, 2)
            })

    with open(report_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Product", "Old Price", "New Price", "Change %"])

        for item in changes:
            writer.writerow([
                item["name"],
                item["old_price"],
                item["new_price"],
                f"{item['change_percent']}%"
            ])

    return changes, report_file
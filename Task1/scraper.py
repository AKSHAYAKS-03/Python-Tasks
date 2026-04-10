import requests
# normal website fetch panna

from bs4 import BeautifulSoup
# HTML parse panna

from playwright.sync_api import sync_playwright
# JS websites scrape panna

from datetime import datetime
from utils import get_random_headers, random_delay, log, clean_price
from db import init_db, save_products
from reporter import generate_price_change_report

BASE_URL = "https://scrapeme.live/shop/page/{}/"
TOTAL_PAGES = 5  


def fetch_page(url, retries=3):
    for attempt in range(1, retries + 1):
        try:
            headers = get_random_headers()
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                return response.text

            elif response.status_code == 429:
                log(f"Rate limited (429). Retry {attempt}/{retries}")
                random_delay(3, 6)

            else:
                log(f"Failed with status {response.status_code} for {url}")

        except Exception as e:
            log(f"Error fetching {url}: {e}")

        random_delay(2, 4)

    return None


def fetch_page_with_playwright(url):
    try:
        # helps to open browser and load the website
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # browseropens in background
            page = browser.new_page(user_agent=get_random_headers()["User-Agent"])
            page.goto(url, timeout=30000)
            html = page.content()
            browser.close()
            return html
    except Exception as e:
        log(f"Playwright failed for {url}: {e}")
        return None


def parse_products(html):
    soup = BeautifulSoup(html, "lxml")
    products = []

    items = soup.select("li.product")
    # scrapeme.live products

    for item in items:
        name_tag = item.select_one("h2.woocommerce-loop-product__title")
        price_tag = item.select_one("span.woocommerce-Price-amount")
        link_tag = item.select_one("a")

        if not name_tag or not price_tag or not link_tag:
            continue

        name = name_tag.text.strip()
        price_text = price_tag.text.strip()
        price = clean_price(price_text)

        product_link = link_tag["href"]
        sku = product_link.rstrip("/").split("/")[-1]

        products.append({
            "name": name,
            "price": price,
            "sku": sku
        })

    return products


def print_price_changes(changes, report_file):
    print("\n=== Price Change Report ===")
    print("+-------------------------------+-----------+-----------+----------+")
    print("| Product                       | Old Price | New Price | Change   |")
    print("+-------------------------------+-----------+-----------+----------+")

    for item in changes:
        name = item["name"][:29]
        old_price = f"${item['old_price']:.2f}"
        new_price = f"${item['new_price']:.2f}"
        change = f"{item['change_percent']:+.1f}%"

        print(f"| {name:<29} | {old_price:<9} | {new_price:<9} | {change:<8} |")

    print("+-------------------------------+-----------+-----------+----------+")
    print(f"{len(changes)} price changes detected. Report saved to {report_file}")


def main():
    init_db()
    all_products = []

    log("Scraper started — target: scrapeme.live")

    for page_num in range(1, TOTAL_PAGES + 1):
        url = BASE_URL.format(page_num)

        html = fetch_page(url)

        if not html:
            log(f"Trying Playwright for page {page_num}")
            html = fetch_page_with_playwright(url)

        if html:
            products = parse_products(html)
            all_products.extend(products)
            log(f"Page {page_num}/{TOTAL_PAGES} — {len(products)} products extracted")
        else:
            log(f"Page {page_num}/{TOTAL_PAGES} — Failed to scrape")

        random_delay(1, 2)

    # first compare
    changes, report_file = generate_price_change_report(all_products)
    print_price_changes(changes, report_file)

    # then save current scrape
    save_products(all_products)
    log(f"Total: {len(all_products)} products saved to DB")

if __name__ == "__main__":
    main()
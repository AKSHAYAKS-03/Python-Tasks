from datetime import datetime
from urllib.parse import urlparse

from database import init_db, save_products
from report import detect_price_changes, export_report, print_price_change_report
from scraper import (
    ScraperConfig,
    build_page_url,
    create_session,
    discover_total_pages,
    fetch_page,
    parse_products,
    polite_delay,
)


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")


def scrape_all_pages(base_url: str, config: ScraperConfig) -> list[dict]:
    session = create_session()
    all_products = []
    seen_skus = set()
    total_pages = None
    consecutive_errors = 0

    for page_number in range(1, config.max_pages + 1):
        page_url = build_page_url(base_url, page_number)
        html = fetch_page(session, page_url, config)

        if html is None:
            consecutive_errors += 1
            if consecutive_errors >= config.max_retries:
                log("Too many consecutive errors, stopping scrape.")
                break
            polite_delay(config)
            continue

        consecutive_errors = 0
        total_pages = total_pages or discover_total_pages(html)
        page_products = parse_products(html, page_url)

        if not page_products:
            log(f"Page {page_number} returned no products, stopping pagination.")
            break

        new_products = [
            product for product in page_products if product["sku"] not in seen_skus
        ]
        for product in new_products:
            seen_skus.add(product["sku"])

        if not new_products:
            log(f"Page {page_number} appears to repeat earlier results, stopping pagination.")
            break

        all_products.extend(new_products)
        page_total = total_pages if total_pages else "?"
        log(f"Page {page_number}/{page_total} - {len(new_products)} products extracted")
        polite_delay(config)

        if total_pages and page_number >= total_pages:
            break

    return all_products


def main():
    base_url = "https://webscraper.io/test-sites/e-commerce/static/computers/laptops"
    target_host = urlparse(base_url).netloc
    config = ScraperConfig(max_pages=20)

    log(f"Scraper started - target: {target_host}")
    conn = init_db()

    try:
        products = scrape_all_pages(base_url, config)
        if not products:
            log("No products were scraped.")
            return

        save_products(conn, products)
        log(f"Total: {len(products):,} products saved to DB")

        changes, current_date, previous_date = detect_price_changes(conn)
        if not changes:
            log(
                f"No price changes found for {current_date}, or no snapshot exists for {previous_date}."
            )
            return

        print_price_change_report(changes, previous_date, current_date)
        report_path = export_report(changes, current_date)
        log(f"Report saved to {report_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

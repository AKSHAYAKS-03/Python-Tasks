import hashlib
import random
import re
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

BLOCK_HINTS = (
    "captcha",
    "access denied",
    "temporarily unavailable",
    "unusual traffic",
    "verify you are human",
)


@dataclass
class ScraperConfig:
    max_pages: int = 50
    max_retries: int = 3
    request_timeout: int = 20
    min_delay: float = 1.0
    max_delay: float = 2.5
    use_browser_fallback: bool = True


def create_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    session.headers.update(
        {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
        }
    )
    return session


def rotate_headers(session: requests.Session) -> None:
    session.headers["User-Agent"] = random.choice(USER_AGENTS)


def polite_delay(config: ScraperConfig) -> None:
    time.sleep(random.uniform(config.min_delay, config.max_delay))


def fetch_page(
    session: requests.Session,
    url: str,
    config: ScraperConfig,
    require_browser: bool = False,
) -> Optional[str]:
    last_error = None

    for attempt in range(1, config.max_retries + 1):
        rotate_headers(session)

        try:
            response = session.get(
                url,
                timeout=config.request_timeout,
                allow_redirects=True,
            )

            if response.status_code in (403, 429):
                raise requests.HTTPError(
                    f"HTTP {response.status_code} received, likely bot protection or rate limiting."
                )

            response.raise_for_status()
            html = response.text

            if require_browser or page_looks_blocked(html):
                browser_html = render_with_browser(url) if config.use_browser_fallback else None
                if browser_html:
                    return browser_html

            return html
        except requests.RequestException as exc:
            last_error = exc
            wait_seconds = min(2 ** attempt, 10) + random.uniform(0.2, 0.8)
            print(
                f"Request failed for {url} "
                f"(attempt {attempt}/{config.max_retries}): {exc}"
            )
            if attempt < config.max_retries:
                time.sleep(wait_seconds)

    print(f"Giving up on {url}: {last_error}")
    return None


def page_looks_blocked(html: str) -> bool:
    normalized = html.lower()
    return any(hint in normalized for hint in BLOCK_HINTS)


def render_with_browser(url: str) -> Optional[str]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(user_agent=random.choice(USER_AGENTS))
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            html = page.content()
            context.close()
            browser.close()
            return html
    except Exception as exc:
        print(f"Browser fallback failed for {url}: {exc}")
        return None


def parse_products(html: str, page_url: str) -> list[dict]:
    soup = build_soup(html)
    products = []

    cards = soup.select(".thumbnail, .product-wrapper, .product-item")

    for card in cards:
        name_tag = card.select_one(".title, .product-title, h4 a, h3 a, h2 a")
        price_tag = card.select_one(".price, .product-price, [data-price]")

        if not name_tag or not price_tag:
            continue

        name = name_tag.get_text(" ", strip=True)
        price_text = price_tag.get("data-price") or price_tag.get_text(strip=True)
        cleaned_price = re.sub(r"[^\d.]", "", price_text)
        if not cleaned_price:
            continue

        product_href = name_tag.get("href", "").strip()
        product_url = urljoin(page_url, product_href) if product_href else page_url
        sku = extract_sku(card, product_url, name)

        products.append(
            {
                "sku": sku,
                "name": name,
                "price": float(cleaned_price),
                "url": product_url,
            }
        )

    return dedupe_products(products)


def extract_sku(card, product_url: str, name: str) -> str:
    explicit = (
        card.get("data-sku")
        or card.get("data-id")
        or card.get("id")
    )
    if explicit:
        return str(explicit).strip()

    parsed = urlparse(product_url)
    slug = parsed.path.rstrip("/").split("/")[-1]
    if slug:
        return slug

    digest = hashlib.sha1(f"{name}|{product_url}".encode("utf-8")).hexdigest()
    return digest[:12]


def dedupe_products(products: list[dict]) -> list[dict]:
    unique = {}
    for product in products:
        unique[product["sku"]] = product
    return list(unique.values())


def discover_total_pages(html: str) -> int:
    soup = build_soup(html)
    page_values = []

    for link in soup.select(".pagination a, a[rel='next'], a[href*='page=']"):
        href = link.get("href", "")
        text = link.get_text(strip=True)

        if text.isdigit():
            page_values.append(int(text))

        parsed = urlparse(href)
        query_page = parse_qs(parsed.query).get("page")
        if query_page and query_page[0].isdigit():
            page_values.append(int(query_page[0]))

    return max(page_values, default=1)


def build_page_url(base_url: str, page_number: int) -> str:
    parsed = urlparse(base_url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page_number)]
    new_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def build_soup(html: str) -> BeautifulSoup:
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return BeautifulSoup(html, "html.parser")

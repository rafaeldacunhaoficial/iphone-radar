"""Amazon.com.br scraper – parse SSR search results HTML."""
import re
import logging
from bs4 import BeautifulSoup
from . import _http

logger = logging.getLogger(__name__)

URL = (
    "https://www.amazon.com.br/s"
    "?k=iphone+apple&rh=n%3A16244559011"
    "&sort=price-asc-rank"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
IPHONE_RE = re.compile(r"i[Pp]hone", re.IGNORECASE)


def get_prices() -> list[dict]:
    try:
        r = _http.get(URL, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as exc:
        logger.warning("amazon fetch error: %s", exc)
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select('[data-component-type="s-search-result"]')
    if not cards:
        logger.warning("amazon: 0 cards found (html size=%d)", len(r.text))
        return []

    results = []
    for card in cards:
        title_el = card.select_one("h2 span")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not IPHONE_RE.search(title):
            continue

        whole_el = card.select_one(".a-price-whole")
        frac_el = card.select_one(".a-price-fraction")
        if not whole_el:
            continue

        whole = re.sub(r"[^0-9]", "", whole_el.get_text())
        frac = re.sub(r"[^0-9]", "", frac_el.get_text()) if frac_el else "00"
        if not whole:
            continue

        try:
            price = float(f"{whole}.{frac[:2]}")
        except ValueError:
            continue
        if price <= 0:
            continue

        results.append({"store": "amazon", "model": title, "price": price})

    logger.info("amazon: %d iPhones", len(results))
    return results

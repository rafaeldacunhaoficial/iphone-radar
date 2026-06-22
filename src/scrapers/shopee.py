"""Shopee Brasil scraper – search API v4."""
import re
import logging
from . import _http

logger = logging.getLogger(__name__)

URL = (
    "https://shopee.com.br/api/v4/search/search_items"
    "?by=relevancy&keyword=iphone+apple&limit=60&newest=0"
    "&order=desc&page_type=search&scenario=PAGE_GLOBAL_SEARCH&version=2"
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "X-Shopee-Language": "pt",
    "Referer": "https://shopee.com.br/search?keyword=iphone+apple",
}
IPHONE_RE = re.compile(r"\biphone\b", re.IGNORECASE)
# Price in Shopee is stored as cents * 1000 (divide by 100000)
PRICE_DIVISOR = 100_000


def get_prices() -> list[dict]:
    try:
        r = _http.get(URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning("shopee fetch error: %s", exc)
        return []

    results = []
    for item in data.get("items", []):
        basic = item.get("item_basic", {})
        name = basic.get("name", "")
        if not IPHONE_RE.search(name):
            continue
        raw_price = basic.get("price") or basic.get("price_min")
        if not raw_price:
            continue
        price = float(raw_price) / PRICE_DIVISOR
        if price <= 0:
            continue
        results.append({"store": "shopee", "model": name, "price": price})

    logger.info("shopee: %d iPhones", len(results))
    return results

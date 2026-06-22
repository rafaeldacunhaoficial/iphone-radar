"""Bemol scraper – VTEX legacy catalog API."""
import re
import logging
from . import _http

logger = logging.getLogger(__name__)

URL = (
    "https://bemol.vtexcommercestable.com.br"
    "/api/catalog_system/pub/products/search"
    "?ft=iphone&_from=0&_to=49"
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.bemol.com.br/",
}
IPHONE_RE = re.compile(r"^Apple\s+i[Pp]hone\s+\d", re.IGNORECASE)


def get_prices() -> list[dict]:
    try:
        r = _http.get(URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        products = r.json()
    except Exception as exc:
        logger.warning("bemol fetch error: %s", exc)
        return []

    results = []
    for p in products:
        name = p.get("productName", "")
        if not IPHONE_RE.match(name):
            continue
        try:
            offer = p["items"][0]["sellers"][0]["commertialOffer"]
            price = float(offer["Price"])
            qty = int(offer.get("AvailableQuantity", 0))
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if price <= 0 or qty <= 0:
            continue
        results.append({"store": "bemol", "model": name, "price": price})

    logger.info("bemol: %d iPhones", len(results))
    return results

"""MercadoLivre scraper – REST API (no CORS from server-side)."""
import re
import logging
from ._http import get_session

logger = logging.getLogger(__name__)

# MLB1055 = Celulares e Smartphones category
URL = (
    "https://api.mercadolibre.com/sites/MLB/search"
    "?q=iphone+apple&category=MLB1055"
    "&condition=new&limit=50&sort=price_asc"
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; iphone-radar/1.0)",
    "Accept": "application/json",
}
IPHONE_RE = re.compile(r"\biPhone\b", re.IGNORECASE)


def get_prices() -> list[dict]:
    session = get_session()
    try:
        r = session.get(URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning("mercadolivre fetch error: %s", exc)
        return []

    results = []
    for item in data.get("results", []):
        title = item.get("title", "")
        if not IPHONE_RE.search(title):
            continue
        price = item.get("price")
        currency = item.get("currency_id", "BRL")
        if not price or float(price) <= 0:
            continue
        if currency != "BRL":
            continue
        results.append({"store": "mercadolivre", "model": title, "price": float(price)})

    logger.info("mercadolivre: %d iPhones", len(results))
    return results

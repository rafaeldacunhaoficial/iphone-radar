"""KaBuM scraper – grupokabum catalog API."""
import re
import logging
from ._http import get_session

logger = logging.getLogger(__name__)

URL = (
    "https://servicespub.prod.api.aws.grupokabum.com.br"
    "/catalog/v2/products"
    "?page_number=1&page_size=60&sort=most_searched"
    "&variant=retail&is_prime=false&query=iphone"
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Origin": "https://www.kabum.com.br",
    "Referer": "https://www.kabum.com.br/",
}
IPHONE_RE = re.compile(r"i[Pp]hone", re.IGNORECASE)


def get_prices() -> list[dict]:
    session = get_session()
    try:
        r = session.get(URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning("kabum fetch error: %s", exc)
        return []

    results = []
    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        title = attrs.get("title", "")
        if not IPHONE_RE.search(title):
            continue
        price = attrs.get("price_with_discount") or attrs.get("price")
        available = attrs.get("available", False)
        if not price or float(price) <= 0 or not available:
            continue
        results.append({"store": "kabum", "model": title, "price": float(price)})

    logger.info("kabum: %d iPhones", len(results))
    return results

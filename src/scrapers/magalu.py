"""Magalu scraper – parse __NEXT_DATA__ from search page."""
import json
import re
import logging
from ._http import get_session

logger = logging.getLogger(__name__)

URL = "https://www.magazineluiza.com.br/busca/iphone/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
IPHONE_RE = re.compile(r"i[Pp]hone", re.IGNORECASE)
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL)


def get_prices() -> list[dict]:
    session = get_session()
    try:
        r = session.get(URL, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as exc:
        logger.warning("magalu fetch error: %s", exc)
        return []

    m = NEXT_DATA_RE.search(r.text)
    if not m:
        logger.warning("magalu: __NEXT_DATA__ not found (html size=%d)", len(r.text))
        return []

    try:
        data = json.loads(m.group(1))
        products = (
            data["props"]["pageProps"]["data"]["search"]["products"]
        )
    except (KeyError, json.JSONDecodeError) as exc:
        logger.warning("magalu parse error: %s", exc)
        return []

    results = []
    for p in products:
        title = p.get("title", "")
        if not IPHONE_RE.search(title):
            continue
        price_obj = p.get("price", {})
        price_str = price_obj.get("fullPrice") or price_obj.get("bestPrice") or price_obj.get("price")
        if not price_str:
            continue
        try:
            price = float(str(price_str).replace(",", "."))
        except ValueError:
            continue
        if price <= 0:
            continue
        results.append({"store": "magalu", "model": title, "price": price})

    logger.info("magalu: %d iPhones", len(results))
    return results

"""Amazon.com.br scraper – parse SSR search results HTML."""

import re
import logging
import requests
from bs4 import BeautifulSoup
from . import _http

logger = logging.getLogger(__name__)

URL = "https://www.amazon.com.br/s?k=iphone+apple&rh=n%3A16244559011&s=price-asc-rank"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.amazon.com.br/",
}

IPHONE_RE = re.compile(r"iphone", re.IGNORECASE)
ACCESSORY_RE = re.compile(
    r"(capa|capinha|pel[ií]cula|case|carregador|cabo|fone|airpod|watch|ipad|suporte|protetor)",
    re.IGNORECASE,
)
PRICE_RS_RE = re.compile(r"R\$\s*([\d.]+),([\d]{2})")


def _parse_price_whole(whole_el, frac_el):
    text = whole_el.get_text(strip=True).rstrip(",").replace(".", "")
    if frac_el:
        text = f"{text}.{frac_el.get_text(strip=True)}"
    try:
        return float(text)
    except ValueError:
        return None


def _parse_price_offscreen(offscreen_el):
    text = offscreen_el.get_text(strip=True)
    m = PRICE_RS_RE.search(text)
    if not m:
        return None
    try:
        return float(f"{m.group(1).replace('.', '')}.{m.group(2)}")
    except ValueError:
        return None


def _fetch_html():
    """Try plain requests first, fall back to cloudscraper via _http."""
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=30)
        if resp.status_code == 200 and len(resp.text) > 50000:
            return resp.text, "requests"
    except Exception:
        pass
    try:
        resp = _http.get(URL, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.text, "cloudscraper"
    except Exception:
        pass
    return None, "failed"


def get_prices() -> list[dict]:
    html, method = _fetch_html()

    if not html:
        get_prices._last_debug = {"error": "fetch failed", "method": method}
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select('[data-component-type="s-search-result"]')
    results = []
    no_price_count = 0

    for card in cards:
        title_el = (
            card.select_one("h2 span")
            or card.select_one(".a-size-base-plus")
            or card.select_one(".a-size-medium")
            or card.select_one("h2")
        )
        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        if not IPHONE_RE.search(title):
            continue
        if ACCESSORY_RE.search(title):
            continue

        price = None
        whole_el = card.select_one(".a-price-whole")
        if whole_el:
            price = _parse_price_whole(whole_el, card.select_one(".a-price-fraction"))

        if price is None:
            offscreen_el = card.select_one(".a-price .a-offscreen")
            if offscreen_el:
                price = _parse_price_offscreen(offscreen_el)

        if price is None or price < 500:
            no_price_count += 1
            continue

        results.append({
            "store": "amazon",
            "model": title[:80],
            "price": price,
        })

    get_prices._last_debug = {
        "count": len(results),
        "html_size": len(html),
        "method": method,
        "cards": len(cards),
        "no_price": no_price_count,
        "sample_titles": [
            (card.select_one("h2 span") or card.select_one("h2") or card)
            .get_text(strip=True)[:60]
            for card in cards[:5]
            if (card.select_one("h2 span") or card.select_one("h2"))
        ],
    }
    logger.info(f"[amazon] {len(results)} iPhones via {method}")
    return results


get_prices._last_debug = {}

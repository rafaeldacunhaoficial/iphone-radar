"""Amazon.com.br scraper – parse SSR search results HTML."""

import re
import logging
import requests
from bs4 import BeautifulSoup

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

_last_debug: dict = {}


def _parse_price_whole(whole_el, frac_el) -> float | None:
    """Parse from .a-price-whole + .a-price-fraction elements."""
    text = whole_el.get_text(strip=True).rstrip(",")
    text = text.replace(".", "")  # remove thousand sep
    if frac_el:
        frac = frac_el.get_text(strip=True)
        text = f"{text}.{frac}"
    try:
        return float(text)
    except ValueError:
        return None


def _parse_price_offscreen(offscreen_el) -> float | None:
    """Parse from .a-price .a-offscreen which contains 'R$ 1.790,00'."""
    text = offscreen_el.get_text(strip=True)
    m = PRICE_RS_RE.search(text)
    if not m:
        return None
    whole = m.group(1).replace(".", "")
    frac = m.group(2)
    try:
        return float(f"{whole}.{frac}")
    except ValueError:
        return None


def get_prices() -> list[dict]:
    global _last_debug
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=30)
        html_size = len(resp.text)

        if resp.status_code != 200:
            _last_debug = {"error": f"HTTP {resp.status_code}", "html_size": html_size}
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
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

            # Try .a-price-whole first (faster path)
            price = None
            whole_el = card.select_one(".a-price-whole")
            if whole_el:
                frac_el = card.select_one(".a-price-fraction")
                price = _parse_price_whole(whole_el, frac_el)

            # Fallback: .a-price .a-offscreen (e.g. "R$ 1.790,00")
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

        _last_debug = {
            "count": len(results),
            "html_size": html_size,
            "cards": len(cards),
            "no_price": no_price_count,
            "sample_titles": [
                (card.select_one("h2 span") or card.select_one("h2") or card)
                .get_text(strip=True)[:60]
                for card in cards[:5]
                if (card.select_one("h2 span") or card.select_one("h2"))
            ],
        }
        logger.info(f"[amazon] {len(results)} iPhones")
        return results

    except Exception as e:
        _last_debug = {"error": str(e)}
        logger.error(f"[amazon] {e}")
        return []

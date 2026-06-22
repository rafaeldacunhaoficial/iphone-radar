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
    "Accept-Encoding": "gzip, deflate, br",
}
IPHONE_RE = re.compile(r"iphone", re.IGNORECASE)


def get_prices() -> list[dict]:
    try:
        r = _http.get(URL, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as exc:
        logger.warning("amazon fetch error: %s", exc)
        get_prices._last_debug = {"error": str(exc)}
        return []

    html_size = len(r.text)
    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select('[data-component-type="s-search-result"]')

    # Collect all h2 span texts for debug
    sample_titles = []
    for card in cards[:5]:
        spans = card.select("h2 span")
        for sp in spans:
            t = sp.get_text(strip=True)
            if t:
                sample_titles.append(t[:80])
                break

    if not cards:
        get_prices._last_debug = {"error": "0 cards", "html_size": html_size}
        return []

    results = []
    for card in cards:
        # Try multiple selectors for title
        title = ""
        for sel in ["h2 span", ".a-size-base-plus", ".a-size-medium", "h2"]:
            el = card.select_one(sel)
            if el:
                title = el.get_text(strip=True)
                if title:
                    break
        if not title or not IPHONE_RE.search(title):
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

    get_prices._last_debug = {
        "count": len(results), "html_size": html_size,
        "cards": len(cards), "sample_titles": sample_titles
    }
    logger.info("amazon: %d iPhones (cards=%d)", len(results), len(cards))
    return results

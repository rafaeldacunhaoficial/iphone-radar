"""Casas Bahia scraper – HTML listing page + SSR product detail prices."""
import re
import logging
import requests
from bs4 import BeautifulSoup
from . import _http

logger = logging.getLogger(__name__)

LIST_URL = "https://www.casasbahia.com.br/iphone/b"
BASE_URL = "https://www.casasbahia.com.br"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.casasbahia.com.br/",
}
PRICE_RE = re.compile(r"R\$\s*([\d.]+),([\d]{2})")
PRODUCT_URL_RE = re.compile(r"/p/(\d+)$")
IPHONE_RE = re.compile(r"iphone", re.IGNORECASE)
BLACKLIST = [
    "capa", "capinha", "pelicula", "case", "carregador",
    "cabo", "fone", "airpods", "watch", "ipad", "suporte",
    "holder", "recondicionado", "seminovo", "usado",
]
MAX_PRODUCTS = 12


def _fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200 and len(r.text) > 3000:
            return r.text
    except Exception:
        pass
    try:
        r = _http.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return None


def _parse_pix_price(html: str):
    """Extract PIX price from product detail page SSR HTML."""
    # Pattern: "no PIX com X% de desconto" preceded by "por R$X.XXX,XX"
    # Also try: just find the last visible price on the page (PIX is last/lowest)
    matches = PRICE_RE.findall(html)
    prices = []
    for whole, frac in matches:
        try:
            p = float(whole.replace(".", "") + "." + frac)
            if p > 500:
                prices.append(p)
        except ValueError:
            pass
    if not prices:
        return None
    # PIX price is typically the lowest / last one shown before "no PIX"
    return min(prices)


def _get_product_links(listing_html: str) -> list:
    """Extract iPhone product URLs from listing page."""
    soup = BeautifulSoup(listing_html, "html.parser")
    links = []
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        title = (a.get_text(strip=True) or a.get("title") or a.get("aria-label") or "")
        if not IPHONE_RE.search(title) and not IPHONE_RE.search(href):
            continue
        if any(w in title.lower() for w in BLACKLIST):
            continue
        if not PRODUCT_URL_RE.search(href):
            continue
        if href in seen:
            continue
        seen.add(href)
        full_url = href if href.startswith("http") else BASE_URL + href
        links.append((title[:80] or "iPhone", full_url))
        if len(links) >= MAX_PRODUCTS:
            break
    return links


def get_prices() -> list[dict]:
    listing_html = _fetch(LIST_URL)
    if not listing_html:
        get_prices._last_debug = {"error": "listing fetch failed"}
        return []

    product_links = _get_product_links(listing_html)
    if not product_links:
        get_prices._last_debug = {
            "error": "no product links found",
            "listing_size": len(listing_html),
        }
        return []

    results = []
    seen_ids = set()
    price_failures = 0

    for title, url in product_links:
        pid_m = PRODUCT_URL_RE.search(url)
        pid = f"cb_{pid_m.group(1)}" if pid_m else f"cb_{abs(hash(url)) % 9999999}"
        if pid in seen_ids:
            continue

        detail_html = _fetch(url)
        if not detail_html:
            price_failures += 1
            continue

        price = _parse_pix_price(detail_html)
        if not price:
            price_failures += 1
            continue

        seen_ids.add(pid)
        # Clean up title from detail page if we have it
        soup = BeautifulSoup(detail_html, "html.parser")
        h1 = soup.find("h1")
        clean_title = h1.get_text(strip=True)[:120] if h1 else title

        results.append({
            "store": "casasbahia",
            "model": clean_title,
            "title": clean_title,
            "price": price,
            "url": url,
            "seller": "Casas Bahia",
            "product_id": pid,
        })

    get_prices._last_debug = {
        "count": len(results),
        "links_found": len(product_links),
        "price_failures": price_failures,
    }
    logger.info(f"[casasbahia] {len(results)} iPhones")
    return results


get_prices._last_debug = {}

"""PMGImports scraper – NuvemShop SSR page."""
import re
import logging
import requests
from bs4 import BeautifulSoup
from . import _http

logger = logging.getLogger(__name__)

URL = "https://pmgimports.com.br/iphones/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
PRICE_RE = re.compile(r"R\$\s*([\d.]+),([\d]{2})")
BLACKLIST = ["capa", "capinha", "pelicula", "case", "carregador", "cabo", "fone", "airpods"]


def _parse_price(text):
    """Return last R$X.XXX,XX price found in text (Pix price is last)."""
    matches = PRICE_RE.findall(text)
    if not matches:
        return None
    whole, frac = matches[-1]
    try:
        return float(whole.replace(".", "") + "." + frac)
    except ValueError:
        return None


def get_prices() -> list[dict]:
    html = None
    method = "none"
    try:
        r = requests.get(URL, headers=HEADERS, timeout=20)
        if r.status_code == 200 and len(r.text) > 5000:
            html = r.text
            method = "requests"
    except Exception:
        pass
    if not html:
        try:
            r = _http.get(URL, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                html = r.text
                method = "cloudscraper"
        except Exception as e:
            get_prices._last_debug = {"error": str(e), "method": "failed"}
            return []

    if not html:
        get_prices._last_debug = {"error": "empty html", "method": method}
        return []

    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "/produtos/" not in href:
            continue
        text = a.get_text(separator=" ", strip=True)
        if "com Pix" not in text and "pix" not in text.lower():
            continue
        title = a.get("title") or ""
        if not title or "iphone" not in title.lower():
            continue
        if any(w in title.lower() for w in BLACKLIST):
            continue
        price = _parse_price(text)
        if not price or price < 500:
            continue
        if title in seen:
            continue
        seen.add(title)
        url = href if href.startswith("http") else "https://pmgimports.com.br" + href
        results.append({
            "store": "pmgimports",
            "model": title[:80],
            "title": title[:80],
            "price": price,
            "url": url,
            "seller": "PMG Imports",
            "product_id": f"pmg_{abs(hash(title)) % 9999999}",
        })

    get_prices._last_debug = {
        "count": len(results),
        "html_size": len(html),
        "method": method,
        "anchors_found": len(soup.find_all("a", href=True)),
    }
    logger.info(f"[pmgimports] {len(results)} iPhones via {method}")
    return results


get_prices._last_debug = {}

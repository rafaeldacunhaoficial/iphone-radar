"""Terabyte Shop scraper – via vtexcommercestable subdomain (bypassa Cloudflare)."""
import logging
import requests
from . import _http

logger = logging.getLogger(__name__)

# vtexcommercestable bypassa CF Bot Fight Mode (igual ao bemol)
BASE = "https://terabyteshop.vtexcommercestable.com.br"
SHELF_URL = BASE + "/_v/api/intelligent-search/product_search/shelf"
CATALOG_URL = BASE + "/api/catalog_system/pub/products/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
BLACKLIST = [
    "capa", "capinha", "pelicula", "case", "carregador",
    "cabo", "fone", "airpods", "watch", "ipad", "suporte",
    "holder", "recondicionado", "seminovo", "usado",
]


def _is_blacklisted(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in BLACKLIST)


def _fetch_shelf() -> list:
    """VTEX IS Shelf API."""
    params = {"query": "iphone", "count": "50", "locale": "pt-BR"}
    try:
        resp = requests.get(SHELF_URL, params=params, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            resp = _http.get(SHELF_URL, params=params, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
        data = resp.json()
        products = (
            data.get("products")
            or data.get("data", {}).get("productSearch", {}).get("products")
            or []
        )
        results = []
        for p in products:
            name = p.get("productName") or p.get("name") or ""
            if not name or _is_blacklisted(name):
                continue
            if "iphone" not in name.lower():
                continue
            items = p.get("items") or []
            for item in items:
                for seller in item.get("sellers") or []:
                    co = seller.get("commertialOffer") or {}
                    price = co.get("spotPrice") or co.get("Price") or 0
                    if price and float(price) > 500:
                        pid = f"tb_{p.get('productId') or abs(hash(name)) % 9999999}"
                        url = p.get("link") or p.get("linkText") or ""
                        if url and not url.startswith("http"):
                            url = "https://www.terabyteshop.com.br/" + url
                        results.append({
                            "store": "terabyte",
                            "model": name[:120],
                            "title": name[:120],
                            "price": float(price),
                            "url": url,
                            "seller": "Terabyte Shop",
                            "product_id": pid,
                        })
                        break  # first valid seller
        return results
    except Exception as e:
        logger.warning(f"[terabyte] shelf error: {e}")
        return []


def _fetch_catalog() -> list:
    """VTEX legacy catalog API fallback."""
    try:
        params = {"ft": "iphone", "_from": 0, "_to": 49}
        resp = requests.get(CATALOG_URL, params=params, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            resp = _http.get(CATALOG_URL, params=params, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
        products = resp.json()
        if not isinstance(products, list):
            return []
        results = []
        for p in products:
            name = p.get("productName") or ""
            if not name or _is_blacklisted(name):
                continue
            if "iphone" not in name.lower():
                continue
            items = p.get("items") or []
            for item in items:
                for seller in item.get("sellers") or []:
                    co = seller.get("commertialOffer") or {}
                    price = co.get("spotPrice") or co.get("Price") or 0
                    if price and float(price) > 500:
                        pid = f"tb_{p.get('productId') or abs(hash(name)) % 9999999}"
                        link = p.get("link") or ""
                        results.append({
                            "store": "terabyte",
                            "model": name[:120],
                            "title": name[:120],
                            "price": float(price),
                            "url": link,
                            "seller": "Terabyte Shop",
                            "product_id": pid,
                        })
                        break
        return results
    except Exception as e:
        logger.warning(f"[terabyte] catalog error: {e}")
        return []


def get_prices() -> list[dict]:
    results = _fetch_shelf()
    method = "shelf"
    if not results:
        results = _fetch_catalog()
        method = "catalog"

    # Deduplicate by product_id
    seen = set()
    deduped = []
    for r in results:
        if r["product_id"] not in seen:
            seen.add(r["product_id"])
            deduped.append(r)

    get_prices._last_debug = {
        "count": len(deduped),
        "method": method,
        "base": BASE,
    }
    logger.info(f"[terabyte] {len(deduped)} iPhones via {method}")
    return deduped


get_prices._last_debug = {}

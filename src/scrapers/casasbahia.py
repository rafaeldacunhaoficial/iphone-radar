"""Casas Bahia scraper – vtexcommercestable subdomain (bypassa CF)."""
import logging
import requests
from . import _http

logger = logging.getLogger(__name__)

BASE = "https://casasbahia.vtexcommercestable.com.br"
SHELF_URL = BASE + "/_v/api/intelligent-search/product_search/shelf"
CATALOG_URL = BASE + "/api/catalog_system/pub/products/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
}
BLACKLIST = [
    "capa", "capinha", "pelicula", "case", "carregador", "cabo", "fone",
    "airpods", "watch", "ipad", "suporte", "holder", "recondicionado",
    "seminovo", "usado", "película", "vidro", "bateria",
]


def _is_blacklisted(t: str) -> bool:
    tl = t.lower()
    return any(w in tl for w in BLACKLIST)


def _parse_products(products: list, store_id="casasbahia") -> list:
    results = []
    for p in products:
        name = p.get("productName") or p.get("name") or ""
        if not name or _is_blacklisted(name):
            continue
        if "iphone" not in name.lower():
            continue
        for item in p.get("items") or []:
            for seller in item.get("sellers") or []:
                co = seller.get("commertialOffer") or {}
                price = co.get("spotPrice") or co.get("Price") or 0
                if price and float(price) > 500:
                    pid = f"cb_{p.get('productId') or abs(hash(name)) % 9999999}"
                    url = p.get("link") or ""
                    if url and not url.startswith("http"):
                        url = "https://www.casasbahia.com.br/" + url
                    results.append({
                        "store": "casasbahia",
                        "model": name[:120],
                        "title": name[:120],
                        "price": float(price),
                        "url": url,
                        "seller": "Casas Bahia",
                        "product_id": pid,
                    })
                    break
    return results


def get_prices() -> list[dict]:
    results = []
    method = "shelf"
    status = None
    try:
        params = {"query": "iphone", "count": "50", "locale": "pt-BR"}
        r = requests.get(SHELF_URL, params=params, headers=HEADERS, timeout=20)
        status = r.status_code
        if r.status_code == 200:
            data = r.json()
            products = (
                data.get("products")
                or data.get("data", {}).get("productSearch", {}).get("products")
                or []
            )
            results = _parse_products(products)
    except Exception as e:
        logger.warning(f"[casasbahia-vtex] shelf: {e}")

    if not results:
        method = "catalog"
        try:
            params = {"ft": "iphone", "_from": 0, "_to": 49}
            r = requests.get(CATALOG_URL, params=params, headers=HEADERS, timeout=20)
            status = r.status_code
            if r.status_code != 200:
                r = _http.get(CATALOG_URL, params=params, headers=HEADERS, timeout=20)
                status = r.status_code
            if r.status_code == 200:
                products = r.json()
                if isinstance(products, list):
                    results = _parse_products(products)
        except Exception as e:
            logger.warning(f"[casasbahia-vtex] catalog: {e}")

    seen = set()
    deduped = [r for r in results if r["product_id"] not in seen and not seen.add(r["product_id"])]
    get_prices._last_debug = {"count": len(deduped), "method": method, "status": status, "base": BASE}
    logger.info(f"[casasbahia] {len(deduped)} iPhones via {method}")
    return deduped


get_prices._last_debug = {}

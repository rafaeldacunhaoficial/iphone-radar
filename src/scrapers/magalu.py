"""Magazine Luiza scraper – API pública de busca."""
import logging
import requests
from . import _http

logger = logging.getLogger(__name__)

# Magalu usa API própria (não VTEX)
SEARCH_URL = "https://www.magazineluiza.com.br/busca/api/v1/search"
# Fallback: endpoint antigo
SEARCH_URL2 = "https://ms.magazineluiza.com.br/luizaproduct/products/v3/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.magazineluiza.com.br/",
}
BLACKLIST = [
    "capa", "capinha", "pelicula", "case", "carregador", "cabo", "fone",
    "airpods", "watch", "ipad", "suporte", "holder", "recondicionado",
    "seminovo", "usado", "película", "vidro", "bateria",
]


def _is_blacklisted(t: str) -> bool:
    tl = t.lower()
    return any(w in tl for w in BLACKLIST)


def _try_api_v1() -> list:
    """Tenta API v1 do Magalu."""
    try:
        params = {"query": "iphone", "page": 1, "limit": 40}
        r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return []
        data = r.json()
        products = data.get("products") or data.get("data") or data.get("result") or []
        if not isinstance(products, list):
            return []
        results = []
        for p in products:
            title = p.get("title") or p.get("name") or p.get("description") or ""
            if not title or _is_blacklisted(title):
                continue
            if "iphone" not in title.lower():
                continue
            price = (
                p.get("price")
                or p.get("sale_price")
                or p.get("bestPrice")
                or p.get("priceTag", {}).get("best_price")
                or 0
            )
            if not price or float(price) < 1000:
                continue
            pid = p.get("id") or p.get("sku") or f"ml_{abs(hash(title)) % 9999999}"
            url = p.get("url") or p.get("link") or "https://www.magazineluiza.com.br/"
            if url and not url.startswith("http"):
                url = "https://www.magazineluiza.com.br" + url
            results.append({
                "store": "magalu",
                "model": title[:120],
                "title": title[:120],
                "price": float(price),
                "url": url,
                "seller": "Magazine Luiza",
                "product_id": f"mg_{pid}",
            })
        return results
    except Exception as e:
        logger.warning(f"[magalu] api_v1: {e}")
        return []


def _try_api_v3() -> list:
    """Tenta API v3 alternativa."""
    try:
        params = {"query": "iphone", "page": 1, "limit": 40}
        r = requests.get(SEARCH_URL2, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            r = _http.get(SEARCH_URL2, params=params, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return []
        data = r.json()
        products = (
            data.get("products")
            or data.get("data", {}).get("products")
            or data.get("result", {}).get("products")
            or []
        )
        results = []
        for p in products:
            title = p.get("title") or p.get("name") or ""
            if not title or _is_blacklisted(title):
                continue
            if "iphone" not in title.lower():
                continue
            price = p.get("price") or p.get("sale_price") or 0
            if not price or float(price) < 1000:
                continue
            pid = p.get("id") or p.get("sku") or f"ml_{abs(hash(title)) % 9999999}"
            url = p.get("url") or "https://www.magazineluiza.com.br/"
            if url and not url.startswith("http"):
                url = "https://www.magazineluiza.com.br" + url
            results.append({
                "store": "magalu",
                "model": title[:120],
                "title": title[:120],
                "price": float(price),
                "url": url,
                "seller": "Magazine Luiza",
                "product_id": f"mg_{pid}",
            })
        return results
    except Exception as e:
        logger.warning(f"[magalu] api_v3: {e}")
        return []


def get_prices() -> list[dict]:
    results = _try_api_v1()
    method = "api_v1"
    if not results:
        results = _try_api_v3()
        method = "api_v3"

    seen = set()
    deduped = []
    for r in results:
        if r["product_id"] not in seen:
            seen.add(r["product_id"])
            deduped.append(r)

    get_prices._last_debug = {"count": len(deduped), "method": method}
    logger.info(f"[magalu] {len(deduped)} iPhones via {method}")
    return deduped


get_prices._last_debug = {}

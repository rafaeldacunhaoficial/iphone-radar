"""
Scraper Casas Bahia - API propria + fallback VTEX.
"""
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.casasbahia.com.br/",
}

IPHONE_QUERIES = [
    ("iPhone 17 Pro Max", "iphone 17 pro max"),
    ("iPhone 17 Pro",     "iphone 17 pro"),
    ("iPhone 17",         "iphone 17"),
    ("iPhone 16 Pro Max", "iphone 16 pro max"),
    ("iPhone 16 Pro",     "iphone 16 pro"),
    ("iPhone 16",         "iphone 16"),
    ("iPhone 15 Pro Max", "iphone 15 pro max"),
    ("iPhone 15 Pro",     "iphone 15 pro"),
    ("iPhone 15",         "iphone 15"),
]

BLACKLIST = ["capa","capinha","pelicula","case","carregador","cabo","fone","airpods","watch","ipad","suporte","holder","recondicionado","seminovo","usado"]


def _get_price(p):
    for pf in ["salePrice", "price", "salesPrice", "bestPrice", "lowPrice", "sellingPrice"]:
        try:
            v = p.get(pf) or (p.get("offers") or {}).get(pf)
            if v:
                return float(v)
        except Exception:
            pass
    return 0


def _try_api(model_name, query):
    try:
        resp = requests.get(
            "https://api.casasbahia.com.br/v1/product/search",
            params={"q": query, "size": 20, "page": 0, "sortBy": "relevance"},
            headers=HEADERS,
            timeout=20,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        products = data.get("products") or data.get("data") or data.get("results") or []
        results = []
        seen = set()
        for p in products[:15]:
            title = p.get("name") or p.get("productName") or p.get("title") or ""
            if not title or title in seen or "iphone" not in title.lower():
                continue
            if any(w in title.lower() for w in BLACKLIST):
                continue
            price = _get_price(p)
            if price < 500:
                continue
            pid = p.get("productId") or p.get("id") or abs(hash(title)) % 9999999
            slug = p.get("linkText") or p.get("slug") or str(pid)
            seen.add(title)
            results.append({
                "store": "casas_bahia",
                "model": model_name,
                "title": title[:120],
                "price": price,
                "url": f"https://www.casasbahia.com.br/{slug}/p",
                "seller": "Casas Bahia",
                "product_id": f"cb_{pid}",
            })
        return results
    except Exception as e:
        logger.warning(f"[CB] API: {e}")
        return []


def _try_vtex(model_name, query):
    try:
        from src.scrapers._vtex_base import scrape_vtex_store
        return scrape_vtex_store("https://www.casasbahia.com.br", "casasbahia", "Casas Bahia")
    except Exception as e:
        logger.warning(f"[CB] VTEX: {e}")
        return []


def _scrape_model(model_name, query):
    r = _try_api(model_name, query)
    return r if r else _try_vtex(model_name, query)


def get_prices():
    results = []
    seen_ids = set()
    for mn, q in IPHONE_QUERIES:
        for it in _scrape_model(mn, q):
            if it["product_id"] not in seen_ids:
                seen_ids.add(it["product_id"])
                results.append(it)
    logger.info(f"[CasasBahia] {len(results)} ofertas.")
    return results

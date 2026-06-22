"""MercadoLivre scraper – public REST API (sem OAuth, sem CF bloqueio)."""
import logging
import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.mercadolibre.com/sites/MLB/search"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}
IPHONE_QUERIES = [
    ("iPhone 17 Pro Max", "iphone 17 pro max apple"),
    ("iPhone 17 Pro",     "iphone 17 pro apple"),
    ("iPhone 17",         "iphone 17 apple"),
    ("iPhone 16 Pro Max", "iphone 16 pro max apple"),
    ("iPhone 16 Pro",     "iphone 16 pro apple"),
    ("iPhone 16",         "iphone 16 apple"),
    ("iPhone 15 Pro Max", "iphone 15 pro max apple"),
    ("iPhone 15 Pro",     "iphone 15 pro apple"),
    ("iPhone 15",         "iphone 15 apple"),
]
BLACKLIST = [
    "capa", "capinha", "pelicula", "case", "carregador",
    "cabo", "fone", "airpods", "watch", "ipad", "suporte",
    "holder", "recondicionado", "seminovo", "usado", "protetor",
]


def _is_blacklisted(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in BLACKLIST)


def _scrape_model(model_name: str, query: str) -> list:
    try:
        params = {
            "q": query,
            "limit": 20,
            "condition": "new",
            "category": "MLB1055",  # Celulares e Smartphones
        }
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            logger.warning(f"[ML] {query}: HTTP {resp.status_code}")
            return []
        data = resp.json()
        results_raw = data.get("results") or []
        results = []
        seen = set()
        for p in results_raw[:20]:
            title = p.get("title") or ""
            if not title or _is_blacklisted(title):
                continue
            if "iphone" not in title.lower():
                continue
            price = p.get("price")
            if not price or float(price) < 1000:
                continue
            pid = p.get("id") or f"ml_{abs(hash(title)) % 9999999}"
            url = p.get("permalink") or f"https://www.mercadolivre.com.br/busca?q={query}"
            if title in seen:
                continue
            seen.add(title)
            results.append({
                "store": "mercadolivre",
                "model": model_name,
                "title": title[:120],
                "price": float(price),
                "url": url,
                "seller": "MercadoLivre",
                "product_id": pid,
            })
        return results
    except Exception as e:
        logger.warning(f"[ML] {query}: {e}")
        return []


def get_prices() -> list:
    all_results = []
    seen_ids = set()
    debug_per_query = {}
    for model_name, query in IPHONE_QUERIES:
        items = _scrape_model(model_name, query)
        debug_per_query[query] = {"count": len(items)}
        for it in items:
            if it["product_id"] not in seen_ids:
                seen_ids.add(it["product_id"])
                all_results.append(it)
    logger.info(f"[ML] Total: {len(all_results)} iPhones")
    get_prices._last_debug = {
        "count": len(all_results),
        "queries": debug_per_query,
    }
    return all_results


get_prices._last_debug = {}

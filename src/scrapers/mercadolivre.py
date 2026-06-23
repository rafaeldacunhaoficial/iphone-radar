"""MercadoLivre scraper – API pública sem filtros restritivos."""
import logging
import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://api.mercadolibre.com/sites/MLB/search"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
}
# Queries simples — sem "apple" no final, sem condition/category
IPHONE_QUERIES = [
    ("iPhone 17 Pro Max", "iphone 17 pro max 256gb"),
    ("iPhone 17 Pro",     "iphone 17 pro 128gb"),
    ("iPhone 17",         "iphone 17 128gb"),
    ("iPhone 16 Pro Max", "iphone 16 pro max 256gb"),
    ("iPhone 16 Pro",     "iphone 16 pro 128gb"),
    ("iPhone 16",         "iphone 16 128gb"),
    ("iPhone 15 Pro Max", "iphone 15 pro max 256gb"),
    ("iPhone 15",         "iphone 15 128gb"),
    ("iPhone 14",         "iphone 14 128gb"),
]
BLACKLIST = [
    "capa", "capinha", "pelicula", "case", "carregador",
    "cabo", "fone", "airpods", "watch", "ipad", "suporte",
    "holder", "recondicionado", "seminovo", "usado", "protetor",
    "película", "vidro", "tela", "bateria", "tampa",
]


def _is_blacklisted(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in BLACKLIST)


def _scrape_model(model_name: str, query: str) -> tuple[list, dict]:
    debug = {"query": query, "status": None, "count": 0, "error": None}
    try:
        params = {
            "q": query,
            "limit": 30,
            # Sem condition=new e sem category — mais resultados
        }
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=25)
        debug["status"] = resp.status_code
        if resp.status_code != 200:
            debug["error"] = f"HTTP {resp.status_code}"
            return [], debug
        data = resp.json()
        results_raw = data.get("results") or []
        debug["raw_count"] = len(results_raw)
        results = []
        seen = set()
        for p in results_raw:
            title = p.get("title") or ""
            if not title or _is_blacklisted(title):
                continue
            if "iphone" not in title.lower():
                continue
            # Só novos
            cond = (p.get("condition") or "").lower()
            if cond and cond != "new":
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
        debug["count"] = len(results)
        return results, debug
    except Exception as e:
        debug["error"] = str(e)
        logger.warning(f"[ML] {query}: {e}")
        return [], debug


def get_prices() -> list:
    all_results = []
    seen_ids = set()
    debug_queries = {}
    for model_name, query in IPHONE_QUERIES:
        items, dbg = _scrape_model(model_name, query)
        debug_queries[query] = dbg
        for it in items:
            if it["product_id"] not in seen_ids:
                seen_ids.add(it["product_id"])
                all_results.append(it)
    logger.info(f"[ML] Total: {len(all_results)} iPhones")
    get_prices._last_debug = {
        "count": len(all_results),
        "queries": debug_queries,
    }
    return all_results


get_prices._last_debug = {}

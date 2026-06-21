"""Scraper iPlace - Apple Premium Reseller (Oracle Commerce Cloud API)."""
import logging
import requests

logger = logging.getLogger(__name__)

OCC_SEARCH = "https://www.iplace.com.br/ccstoreui/v1/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

IPHONE_QUERIES = [
    "iphone 17 pro max",
    "iphone 17 pro",
    "iphone 17",
    "iphone 16 pro max",
    "iphone 16 pro",
    "iphone 16",
    "iphone 15 pro max",
    "iphone 15 pro",
    "iphone 15",
]

BLACKLIST = [
    "capa", "capinha", "pelicula", "pelíc ula", "case", "carregador",
    "cabo", "fone", "airpods", "watch", "ipad", "suporte", "holder",
    "recondicionado", "seminovo", "usado", "protetor",
]

PAGE_SIZE = 50


def _is_blacklisted(title: str) -> bool:
    return any(w in title.lower() for w in BLACKLIST)


def _get_attr(attrs: dict, key: str):
    val = attrs.get(key)
    if isinstance(val, list) and val:
        return val[0]
    return val


def _scrape_query(query: str) -> tuple:
    results = []
    debug = {"query": query, "total": 0, "count": 0, "error": None}
    try:
        r = requests.get(
            OCC_SEARCH,
            headers=HEADERS,
            params={"Nrpp": PAGE_SIZE, "No": 0, "Ntt": query},
            timeout=30,
        )
        debug["status"] = r.status_code
        if r.status_code != 200:
            debug["error"] = f"HTTP {r.status_code}"
            return results, debug
        data = r.json()
        result_list = data.get("resultsList", {})
        debug["total"] = result_list.get("totalNumRecs", 0)
        for group in result_list.get("records", []):
            skus = group.get("records") or [group]
            for sku_rec in skus:
                attrs = sku_rec.get("attributes", {})
                name = _get_attr(attrs, "sku.displayName") or _get_attr(attrs, "product.displayName")
                if not name or _is_blacklisted(name):
                    continue
                avail = _get_attr(attrs, "sku.availabilityStatus")
                if avail and avail.upper() not in ("INSTOCK", "PREORDERABLE"):
                    continue
                price_raw = _get_attr(attrs, "sku.activePrice") or _get_attr(attrs, "sku.listPrice")
                if not price_raw:
                    continue
                try:
                    price = float(price_raw)
                except (TypeError, ValueError):
                    continue
                if price < 1000:
                    continue
                sku_id = _get_attr(attrs, "sku.repositoryId") or ""
                prod_id = _get_attr(attrs, "product.repositoryId") or ""
                slug = _get_attr(attrs, "product.seoUrlSlug") or ""
                pid = f"iplace_{sku_id or prod_id}"
                url = (
                    f"https://www.iplace.com.br/{slug}/{prod_id}"
                    if slug and prod_id
                    else "https://www.iplace.com.br"
                )
                results.append({
                    "store": "iplace",
                    "model": query.title(),
                    "title": name[:120],
                    "price": price,
                    "url": url[:200],
                    "seller": "iPlace",
                    "product_id": pid,
                })
        debug["count"] = len(results)
    except Exception as e:
        debug["error"] = str(e)
        logger.error(f"[iPlace] {query}: {e}")
    logger.info(f"[iPlace] '{query}': {debug.get('count',0)}/{debug.get('total',0)}")
    return results, debug


def get_prices() -> list:
    all_results = []
    all_debug = {}
    seen = set()
    for query in IPHONE_QUERIES:
        items, dbg = _scrape_query(query)
        for item in items:
            if item["product_id"] not in seen:
                seen.add(item["product_id"])
                all_results.append(item)
        all_debug[query] = dbg
    logger.info(f"[iPlace] Total: {len(all_results)} SKUs unicos")
    get_prices._last_debug = all_debug
    return all_results

"""Scraper Magazine Luiza - __NEXT_DATA__ SSR (props.pageProps.data.search.products)."""
import json
import logging
import re
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

IPHONE_QUERIES = [
    ("iPhone 17 Pro Max", "iphone-17-pro-max"),
    ("iPhone 17 Pro",     "iphone-17-pro"),
    ("iPhone 17",         "iphone-17"),
    ("iPhone 16 Pro Max", "iphone-16-pro-max"),
    ("iPhone 16 Pro",     "iphone-16-pro"),
    ("iPhone 16",         "iphone-16"),
    ("iPhone 15 Pro Max", "iphone-15-pro-max"),
    ("iPhone 15 Pro",     "iphone-15-pro"),
    ("iPhone 15",         "iphone-15"),
]

BLACKLIST = [
    "capa", "capinha", "pelicula", "película", "case", "carregador",
    "cabo", "fone", "airpods", "watch", "ipad", "suporte", "holder",
    "recondicionado", "seminovo", "usado", "protetor",
]


def _is_blacklisted(title: str) -> bool:
    return any(w in title.lower() for w in BLACKLIST)


def _best_price(price_obj) -> float:
    """Extract lowest price from Magalu price dict."""
    if not isinstance(price_obj, dict):
        return 0.0
    for field in ("bestPrice", "salesPrice", "salePrice", "price", "fullPrice"):
        val = price_obj.get(field)
        if val:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return 0.0


def _scrape_model(model_name: str, slug: str) -> tuple:
    debug = {"slug": slug, "status": None, "has_next_data": False, "count": 0, "error": None}
    results = []
    try:
        url = f"https://www.magazineluiza.com.br/busca/{slug}/"
        resp = requests.get(url, headers=HEADERS, timeout=30)
        debug["status"] = resp.status_code
        debug["html_size"] = len(resp.text)
        if resp.status_code != 200:
            debug["error"] = f"HTTP {resp.status_code}"
            return results, debug
        m = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>([sS]*?)</script>',
            resp.text,
        )
        if not m:
            debug["error"] = "no __NEXT_DATA__"
            return results, debug
        debug["has_next_data"] = True
        data = json.loads(m.group(1))
        products = (
            data.get("props", {})
            .get("pageProps", {})
            .get("data", {})
            .get("search", {})
            .get("products", [])
        )
        for p in products:
            if not p.get("available", True):
                continue
            title = (p.get("title") or "").strip()
            if not title or _is_blacklisted(title):
                continue
            price = _best_price(p.get("price", {}))
            if price < 1000:
                continue
            pid = str(p.get("id") or p.get("variationId") or abs(hash(title)) % 9_999_999)
            path = p.get("path") or ""
            purl = (
                "https://www.magazineluiza.com.br" + path
                if path
                else f"https://www.magazineluiza.com.br/-/p/{pid}/"
            )
            seller_obj = p.get("seller") or {}
            seller = (
                seller_obj.get("description") or seller_obj.get("id") or "Magalu"
                if isinstance(seller_obj, dict)
                else str(seller_obj)
            )
            results.append({
                "store": "magalu",
                "model": model_name,
                "title": title[:120],
                "price": price,
                "url": purl[:200],
                "seller": seller,
                "product_id": f"mg_{pid}",
            })
        debug["count"] = len(results)
    except Exception as e:
        debug["error"] = str(e)
        logger.error(f"[Magalu] {slug}: {e}")
    logger.info(
        f"[Magalu] {slug}: status={debug.get('status')} "
        f"next_data={debug['has_next_data']} count={debug['count']}"
    )
    return results, debug


def get_prices() -> list:
    all_results = []
    all_debug = {}
    seen = set()
    for model_name, slug in IPHONE_QUERIES:
        items, dbg = _scrape_model(model_name, slug)
        for item in items:
            if item["product_id"] not in seen:
                seen.add(item["product_id"])
                all_results.append(item)
        all_debug[slug] = dbg
    logger.info(f"[Magalu] Total: {len(all_results)} SKUs unicos")
    get_prices._last_debug = all_debug
    return all_results

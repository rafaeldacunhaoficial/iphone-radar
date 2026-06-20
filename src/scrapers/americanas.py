"""
Scraper Americanas.com.br - tenta multiplos endpoints da API B2W.
"""
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.americanas.com.br/",
    "Origin": "https://www.americanas.com.br",
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

ENDPOINTS = [
    "https://mystique-v2-americanas.b2w.io/data/search",
    "https://api.americanas.com.br/v2/page/",
]


def _get_price(p):
    for pf in ["lowPrice", "salePrice", "sellingPrice", "bestPrice", "price", "salesPrice", "spotPrice"]:
        try:
            v = p.get(pf) or (p.get("offers") or {}).get(pf)
            if v:
                return float(v)
        except Exception:
            pass
    return 0


def _scrape_model(model_name, query):
    for ep in ENDPOINTS:
        try:
            if "page" in ep:
                params = {"identifier": f"/busca/{query.replace(' ', '-')}", "limit": 20}
            else:
                params = {"query": query, "limit": 20, "offset": 0}
            resp = requests.get(ep, params=params, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue
            data = resp.json()
            products = (data.get("data") or {}).get("products") or data.get("data") or []
            if not isinstance(products, list):
                continue
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
                pid = p.get("id") or abs(hash(title)) % 9999999
                url = p.get("url") or f"https://www.americanas.com.br/busca/{query.replace(' ', '%20')}"
                if not url.startswith("http"):
                    url = "https://www.americanas.com.br" + url
                seen.add(title)
                results.append({
                    "store": "americanas",
                    "model": model_name,
                    "title": title[:120],
                    "price": price,
                    "url": url,
                    "seller": "Americanas",
                    "product_id": f"ame_{pid}",
                })
            if results:
                return results
        except Exception as e:
            logger.warning(f"[Americanas] {ep}: {e}")
    return []


def get_prices():
    results = []
    seen_ids = set()
    for mn, q in IPHONE_QUERIES:
        for it in _scrape_model(mn, q):
            if it["product_id"] not in seen_ids:
                seen_ids.add(it["product_id"])
                results.append(it)
    logger.info(f"[Americanas] {len(results)} ofertas.")
    return results

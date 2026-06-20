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
    {
        "url": "https://mystique-v2-americanas.b2w.io/data/search",
        "param": "query",
        "path": ["data"],
        "name_field": "name",
        "price_fields": ["offers","lowPrice"],
        "url_field": "url",
        "id_field": "id",
    },
    {
        "url": "https://api.americanas.com.br/v2/page/",
        "param": "identifier",
        "path": ["data","products"],
        "name_field": "name",
        "price_fields": ["offers","lowPrice"],
        "url_field": "url",
        "id_field": "id",
    },
]

def _extract_price(obj, fields):
    if isinstance(fields, list):
        v = obj
        for f in fields:
            if isinstance(v, dict):
                v = v.get(f)
            else:
                return None
        try:
            return float(v)
        except Exception:
            return None
    try:
        return float(obj.get(fields, 0) or 0)
    except Exception:
        return None

def _get_in(obj, path):
    v = obj
    for k in path:
        if isinstance(v, dict):
            v = v.get(k)
        elif isinstance(v, list) and isinstance(k, int):
            v = v[k] if k < len(v) else None
        else:
            return None
    return v

def _scrape_model(model_name, query):
    for ep in ENDPOINTS:
        try:
            params = {ep["param"]: query, "limit": 20, "offset": 0}
            if ep["param"] == "identifier":
                params = {"identifier": f"/busca/{query.replace(' ','-')}", "limit": 20}
            resp = requests.get(ep["url"], params=params, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue
            data = resp.json()
            products = _get_in(data, ep["path"])
            if not products or not isinstance(products, list):
                continue
            results = []
            seen = set()
            for p in products[:15]:
                title = p.get(ep["name_field"], "")
                if not title or title in seen or "iphone" not in title.lower():
                    continue
                if any(w in title.lower() for w in BLACKLIST):
                    continue
                price_raw = p
                for f in ep["price_fields"] if isinstance(ep["price_fields"], list) else [ep["price_fields"]]:
                    price_raw = price_raw.get(f, {}) if isinstance(price_raw, dict) else price_raw
                try:
                    price = float(price_raw) if not isinstance(price_raw, dict) else 0
                except Exception:
                    price = 0
                if price < 500:
                    for pf in ["lowPrice","salePrice","sellingPrice","bestPrice","price","salesPrice","spotPrice"]:
                        try:
                            v = p.get(pf) or (p.get("offers") or {}).get(pf)
                            if v:
                                price = float(v)
                                break
                        except Exception:
                            pass
                if price < 500:
                    continue
                pid = p.get(ep["id_field"], abs(hash(title)) % 9999999)
                url = p.get(ep["url_field"], f"https://www.americanas.com.br/busca/{query.replace(' ','%20')}")
                if not url.startswith("http"):
                    url = "https://www.americanas.com.br" + url
                seen.add(title)
                results.append({"store":"americanas","model":model_name,"title":title[:120],"price":price,"url":url,"seller":"Americanas","product_id":f"ame_{pid}"})
            if results:
                return results
        except Exception as e:
            logger.warning(f"[Americanas] endpoint {ep['url']}: {e}")
    return []

def get_prices():
    results = []; seen_ids = set()
    for mn, q in IPHONE_QUERIES:
        for it in _scrape_model(mn, q):
            if it["product_id"] not in seen_ids:
                seen_ids.add(it["product_id"]); results.append(it)
    logger.info(f"[Americanas] {len(results)} ofertas.")
    return results

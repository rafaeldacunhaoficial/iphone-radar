"""
Base compartilhada para scrapers VTEX.
"""
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

IPHONE_QUERIES = [
    ("iPhone 17 Pro Max", "iphone 17 pro max"),
    ("iPhone 17 Pro", "iphone 17 pro"),
    ("iPhone 17", "iphone 17"),
    ("iPhone 16 Pro Max", "iphone 16 pro max"),
    ("iPhone 16 Pro", "iphone 16 pro"),
    ("iPhone 16", "iphone 16"),
    ("iPhone 15 Pro Max", "iphone 15 pro max"),
    ("iPhone 15 Pro", "iphone 15 pro"),
    ("iPhone 15", "iphone 15"),
]

BLACKLIST = ["capa", "película", "case", "carregador", "capinha", "cabo", "fone", "suporte"]


def _try_catalog_search(base_url, store_id, model_name, query):
    try:
        resp = requests.get(
            f"{base_url}/api/catalog_system/pub/products/search",
            params={"ft": query, "_from": 0, "_to": 4},
            headers=HEADERS, timeout=20
        )
        if resp.status_code != 200 or not resp.text.strip() or resp.text.strip() == "[]":
            return []
        products_raw = resp.json()
        results = []
        for product in products_raw[:5]:
            title = product.get("productName", "")
            if "iphone" not in title.lower() or any(w in title.lower() for w in BLACKLIST):
                continue
            items = product.get("items", [])
            if not items: continue
            sellers = items[0].get("sellers", [])
            if not sellers: continue
            offer = sellers[0].get("commertialOffer", {})
            price = offer.get("Price", 0)
            if price < 500 or offer.get("AvailableQuantity", 0) == 0: continue
            link_text = product.get("linkText", "")
            link = product.get("link") or f"{base_url}/{link_text}/p"
            results.append({"store": store_id, "model": model_name, "title": title[:120],
                "price": float(price), "url": link, "seller": store_id.title(),
                "product_id": f"{store_id}_{product.get('productId', abs(hash(title)) % 999999)}"})
        return results
    except: return []


def _try_intelligent_search(base_url, store_id, model_name, query):
    try:
        gql = {"query": "query ($query:String!){ productSearch(query:%query,from0,to4){ products{ productName priceRange{ sellingPrice{ highPrice lowPrice } } linkText items{ sellers{ commertialOffer{ Price AvailableQuantity } } } } } }",
            "variables": {"query": query}}
        resp = requests.post(f"{base_url}/_v/segment/graphql/v1", json=gql,
            headers={**HEADERS, "Content-Type": "application/json"}, timeout=15)
        if resp.status_code != 200: return []
        products = resp.json().get("data", {}).get("productSearch", {}).get("products", [])
        results = []
        for p in products[:5]:
            title = p.get("productName", "")
            if not title or not "iphone" in title.lower() or any(w in title.lower() for w in BLACKLIST): continue
            price = p.get("priceRange", {}).get("sellingPrice", {}).get("lowPrice", 0)
            if not price or price < 500:
                items = p.get("items", [])
                if items: price = (items[0].get("sellers") or [{}])[0].get("commertialOffer", {}).get("Price", 0)
            if price < 500: continue
            link_text = p.get("linkText", "")
            results.append({"store": store_id, "model": model_name, "title": title[:120],
                "price": float(price), "url": f"{base_url}/{link_text}/p" if link_text else base_url,
                "seller": store_id.title(), "product_id": f"{store_id}_{abs(hash(title)) % 999999}"})
        return results
    except: return []


def scrape_vtex_store(base_url, store_id, display_name):
    results = []
    seen_ids = set()
    for model_name, query in IPHONE_QUERIES:
        items = (_try_catalog_search(base_url, store_id, model_name, query)
                 or _try_intelligent_search(base_url, store_id, model_name, query))
        for item in items:
            if item["product_id"] not in seen_ids:
                seen_ids.add(item["product_id"])
                results.append(item)
    logger.info(f"[{display_name}] {len(results)} ofertas encontradas.")
    return results

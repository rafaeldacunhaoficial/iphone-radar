"""
Scraper Carrefour BR — tenta endpoint direto e fallback no mercado.carrefour.com.br.
"""
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

ENDPOINTS = [
    "https://www.carrefour.com.br/api/catalog_system/pub/products/search",
    "https://mercado.carrefour.com.br/api/catalog_system/pub/products/search",
]

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


def _try_endpoint(endpoint: str, query: str) -> list:
    try:
        resp = requests.get(endpoint, params={"ft": query, "_from": 0, "_to": 4},
                            headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


def _scrape_model(model_name: str, query: str) -> list[dict]:
    data = []
    for ep in ENDPOINTS:
        data = _try_endpoint(ep, query)
        if data:
            break
    results = []
    for product in data[:5]:
        title = product.get("productName", "")
        if "iphone" not in title.lower() or any(w in title.lower() for w in BLACKLIST):
            continue
        items = product.get("items", [])
        if not items:
            continue
        sellers = items[0].get("sellers", [])
        if not sellers:
            continue
        offer = sellers[0].get("commertialOffer", {})
        price = offer.get("Price", 0)
        if price < 500 or offer.get("AvailableQuantity", 0) == 0:
            continue
        link = product.get("link", f"https://www.carrefour.com.br/{product.get('linkText', '')}/p")
        results.append({
            "store": "carrefour",
            "model": model_name,
            "title": title[:120],
            "price": float(price),
            "url": link,
            "seller": "Carrefour",
            "product_id": f"car_{product.get('productId', hash(title) % 999999)}",
        })
    return results


def get_prices() -> list[dict]:
    results = []
    for model_name, query in IPHONE_QUERIES:
        results.extend(_scrape_model(model_name, query))
    logger.info(f"[Carrefour] {len(results)} ofertas encontradas.")
    return results

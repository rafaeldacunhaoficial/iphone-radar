"""
Scraper Ricardo Eletro — rede de eletroeletrônicos (usa VTEX).
"""
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
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


def _scrape_model(model_name: str, query: str) -> list[dict]:
    try:
        resp = requests.get(
            "https://www.ricardoeletro.com.br/api/catalog_system/pub/products/search",
            params={"ft": query, "_from": 0, "_to": 4},
            headers=HEADERS,
            timeout=20,
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        results = []

        for product in data[:5]:
            title = product.get("productName", "")
            if "iphone" not in title.lower():
                continue
            if any(w in title.lower() for w in BLACKLIST):
                continue

            items = product.get("items", [])
            if not items:
                continue
            sellers = items[0].get("sellers", [])
            if not sellers:
                continue

            offer = sellers[0].get("commertialOffer", {})
            price = offer.get("Price", 0)
            available = offer.get("AvailableQuantity", 0)

            if price < 500 or available == 0:
                continue

            link = product.get("link", f"https://www.ricardoeletro.com.br/{product.get('linkText', '')}/p")
            results.append({
                "store": "ricardo",
                "model": model_name,
                "title": title[:120],
                "price": float(price),
                "url": link,
                "seller": "Ricardo Eletro",
                "product_id": f"ric_{product.get('productId', hash(title) % 999999)}",
            })

        return results

    except Exception as e:
        logger.warning(f"[Ricardo Eletro] Erro ao buscar '{query}': {e}")
        return []


def get_prices() -> list[dict]:
    results = []
    for model_name, query in IPHONE_QUERIES:
        items = _scrape_model(model_name, query)
        results.extend(items)
    logger.info(f"[Ricardo Eletro] {len(results)} ofertas encontradas.")
    return results

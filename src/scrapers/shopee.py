"""
Scraper Shopee BR — API publica de busca (sem auth).
Precos no Shopee sao armazenados em centavos x 100000.
"""
import logging
import requests

logger = logging.getLogger(__name__)

API_URL = "https://shopee.com.br/api/v4/search/search_items"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://shopee.com.br/",
    "x-api-source": "pc",
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
BLACKLIST = ["capa", "pelicula", "case", "carregador", "capinha", "cabo", "fone", "suporte"]


def _scrape_model(model_name, query):
    try:
        resp = requests.get(API_URL, params={
            "by": "relevancy", "keyword": query, "limit": 10,
            "newest": 0, "order": "asc", "page_type": "search",
            "scenario": "PAGE_GLOBAL_SEARCH", "version": 2,
        }, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
        results = []
        for item in resp.json().get("items", [])[:8]:
            b = item.get("item_basic", {})
            title = b.get("name", "")
            price_raw = b.get("price", 0)
            if not title or not price_raw:
                continue
            if "iphone" not in title.lower() or any(w in title.lower() for w in BLACKLIST):
                continue
            price = price_raw / 100000
            if price < 500:
                continue
            url = f"https://shopee.com.br/produto/{b.get('shopid')}/{b.get('itemid')}"
            results.append({"store": "shopee", "model": model_name, "title": title[:120],
                "price": round(price, 2), "url": url, "seller": "Shopee BR",
                "product_id": f"shopee_{b.get('itemid')}"})
        return results
    except Exception as e:
        logger.warning(f"[Shopee] Erro: {e}")
        return []


def get_prices():
    results = []
    for model_name, query in IPHONE_QUERIES:
        results.extend(_scrape_model(model_name, query))
    logger.info(f"[Shopee] {len(results)} ofertas encontradas.")
    return results

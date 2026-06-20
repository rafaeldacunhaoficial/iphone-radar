"""
Scraper MercadoLivre - API publica oficial (sem OAauth para buscas).
Documentacao: https://developers.mercadolibre.com.br/pt_br/itens-e-buscas
"""
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PriceBot/1.0)",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

MLB_CELULARES = "MLB1055"

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


def _scrape_model(model_name, query):
    try:
        resp = requests.get(
            "https://api.mercadolibre.com/sites/MLB/search",
            params={"q": query, "limit": 20, "condition": "new", "category": MLB_CELULARES},
            headers=HEADERS,
            timeout=20,
        )
        if resp.status_code != 200:
            return []
        results = []
        seen = set()
        for item in resp.json().get("results", [])[:15]:
            title = item.get("title", "")
            if not title or title in seen or "iphone" not in title.lower():
                continue
            if any(w in title.lower() for w in BLACKLIST):
                continue
            price = float(item.get("price", 0) or 0)
            if price < 500:
                continue
            seen.add(title)
            seller_obj = item.get("seller") or {}
            seller_name = seller_obj.get("nickname", "MercadoLivre")
            item_id = item.get("id", abs(hash(title)) % 9999999)
            purl = item.get("permalink", "https://www.mercadolivre.com.br/")
            results.append({
                "store": "mercadolivre",
                "model": model_name,
                "title": title[:120],
                "price": price,
                "url": purl,
                "seller": seller_name,
                "product_id": f"ml_{item_id}",
            })
        return results
    except Exception as e:
        logger.warning(f"[ML] {e}")
        return []


def get_prices():
    results = []
    seen_ids = set()
    for mn, q in IPHONE_QUERIES:
        for it in _scrape_model(mn, q):
            if it["product_id"] not in seen_ids:
                seen_ids.add(it["product_id"])
                results.append(it)
    logger.info(f"[ML] {len(results)} ofertas.")
    return results

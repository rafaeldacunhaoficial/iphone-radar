"""
Scraper MercadoLivre — usa a API oficial pública (sem auth).
Endpoint: https://api.mercadolibre.com/sites/MLB/search
"""

import requests
import logging
from typing import Optional

logger = logging.getLogger(__name__)

API_BASE = "https://api.mercadolibre.com/sites/MLB/search"

IPHONE_MODELS = [
    "iPhone 17 Pro Max",
    "iPhone 17 Pro",
    "iPhone 17 Plus",
    "iPhone 17",
    "iPhone 16 Pro Max",
    "iPhone 16 Pro",
    "iPhone 16 Plus",
    "iPhone 16",
    "iPhone 15 Pro Max",
    "iPhone 15 Pro",
    "iPhone 15 Plus",
    "iPhone 15",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; iPhoneRadar/1.0)",
    "Accept": "application/json",
}


def _fetch_listings(query: str, limit: int = 20) -> list[dict]:
    """Chama a API do MercadoLivre e retorna os melhores anúncios de novo."""
    try:
        resp = requests.get(
            API_BASE,
            params={"q": query, "limit": limit, "condition": "new", "sort": "price_asc"},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", [])
    except Exception as e:
        logger.warning(f"[ML] Erro ao buscar '{query}': {e}")
        return []


def _is_valid_iphone(title: str, model: str) -> bool:
    """Filtra anúncios que não correspondem ao modelo buscado (capas, películas, etc.)."""
    title_lower = title.lower()
    model_lower = model.lower()

    # Deve conter as palavras-chave do modelo
    parts = model_lower.split()
    if not all(p in title_lower for p in parts):
        return False

    # Exclui acessórios
    blacklist = ["capa", "capinha", "película", "case", "carregador", "cabo",
                 "fone", "airpods", "watch", "ipad", "suporte", "holder",
                 "remanufaturado", "recondicionado", "usado"]
    for word in blacklist:
        if word in title_lower:
            return False

    return True


def get_prices() -> list[dict]:
    """
    Retorna lista de ofertas:
    {
        "store": "mercadolivre",
        "model": "iPhone 16 Pro Max",
        "title": "...",
        "price": 9999.00,
        "url": "https://...",
        "seller": "Apple Store",
        "product_id": "MLB123456"
    }
    """
    results = []
    seen_ids = set()

    for model in IPHONE_MODELS:
        listings = _fetch_listings(model)
        for item in listings:
            item_id = item.get("id", "")
            if item_id in seen_ids:
                continue

            title = item.get("title", "")
            if not _is_valid_iphone(title, model):
                continue

            price = item.get("price")
            if not price or price < 500:  # ignora preços absurdos
                continue

            permalink = item.get("permalink", "")
            seller = (item.get("seller", {}) or {}).get("nickname", "Vendedor")

            seen_ids.add(item_id)
            results.append({
                "store": "mercadolivre",
                "model": model,
                "title": title,
                "price": float(price),
                "url": permalink,
                "seller": seller,
                "product_id": item_id,
            })

    logger.info(f"[ML] {len(results)} ofertas encontradas.")
    return results

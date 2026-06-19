"""
Scraper Magazine Luiza — usa a API interna de busca (JSON).
"""

import logging
import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.magazineluiza.com.br/busca/{query}/?from=submit&page=1"
API_URL = "https://api.magazineluiza.com.br/v3/search/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Origin": "https://www.magazineluiza.com.br",
    "Referer": "https://www.magazineluiza.com.br/",
}

IPHONE_QUERIES = [
    ("iPhone 17 Pro Max", "iphone+17+pro+max"),
    ("iPhone 17 Pro", "iphone+17+pro"),
    ("iPhone 17", "iphone+17"),
    ("iPhone 16 Pro Max", "iphone+16+pro+max"),
    ("iPhone 16 Pro", "iphone+16+pro"),
    ("iPhone 16", "iphone+16"),
    ("iPhone 15 Pro Max", "iphone+15+pro+max"),
    ("iPhone 15 Pro", "iphone+15+pro"),
    ("iPhone 15", "iphone+15"),
]


def _scrape_model(model_name: str, query: str) -> list[dict]:
    try:
        # Magalu tem uma API JSON acessível via query params
        resp = requests.get(
            f"https://www.magazineluiza.com.br/busca/{query}/",
            params={"from": "submit", "page": "1"},
            headers={**HEADERS, "Accept": "text/html"},
            timeout=20,
        )
        if resp.status_code != 200:
            return []

        # Tenta extrair JSON do script de hydration
        import re
        match = re.search(r'"price"\s*:\s*(\d+\.?\d*)', resp.text)
        products_data = re.findall(
            r'"title"\s*:\s*"([^"]+)".*?"price"\s*:\s*(\d+\.?\d*).*?"url"\s*:\s*"([^"]+)"',
            resp.text,
            re.DOTALL,
        )

        results = []
        seen = set()
        for title, price_str, url in products_data[:5]:
            if title in seen:
                continue
            title_lower = title.lower()
            if "iphone" not in title_lower:
                continue
            if any(w in title_lower for w in ["capa", "película", "case", "carregador"]):
                continue
            try:
                price = float(price_str)
            except ValueError:
                continue
            if price < 500:
                continue

            seen.add(title)
            full_url = url if url.startswith("http") else f"https://www.magazineluiza.com.br{url}"
            results.append({
                "store": "magalu",
                "model": model_name,
                "title": title,
                "price": price,
                "url": full_url,
                "seller": "Magazine Luiza",
                "product_id": f"ml_{hash(full_url) % 999999}",
            })

        return results

    except Exception as e:
        logger.warning(f"[Magalu] Erro ao scraper '{query}': {e}")
        return []


def get_prices() -> list[dict]:
    results = []
    for model_name, query in IPHONE_QUERIES:
        items = _scrape_model(model_name, query)
        results.extend(items)
    logger.info(f"[Magalu] {len(results)} ofertas encontradas.")
    return results

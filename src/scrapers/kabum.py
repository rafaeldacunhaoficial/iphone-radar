"""
Scraper Kabum — usa a API de busca pública (JSON).
"""

import logging
import requests

logger = logging.getLogger(__name__)

API_URL = "https://www.kabum.com.br/api/busca"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Origin": "https://www.kabum.com.br",
    "Referer": "https://www.kabum.com.br/",
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


def _scrape_model(model_name: str, query: str) -> list[dict]:
    try:
        # Kabum tem API JSON acessível
        resp = requests.get(
            "https://www.kabum.com.br/api/busca",
            params={
                "string": query,
                "limit": 10,
                "offset": 0,
                "sort": "price_asc",
            },
            headers=HEADERS,
            timeout=20,
        )

        if resp.status_code != 200:
            # Fallback: scraping HTML
            return _scrape_html(model_name, query)

        data = resp.json()
        items = data.get("data", data.get("products", []))
        if not items:
            return _scrape_html(model_name, query)

        results = []
        for item in items[:5]:
            title = item.get("name", item.get("title", ""))
            price = item.get("price", item.get("vlrPreco", 0))
            url = item.get("link", item.get("url", ""))

            if not title or not price:
                continue

            title_lower = title.lower()
            if "iphone" not in title_lower:
                continue
            if any(w in title_lower for w in ["capa", "película", "case", "carregador"]):
                continue
            if float(price) < 500:
                continue

            full_url = url if url.startswith("http") else f"https://www.kabum.com.br{url}"
            results.append({
                "store": "kabum",
                "model": model_name,
                "title": title,
                "price": float(price),
                "url": full_url,
                "seller": "KaBuM!",
                "product_id": f"kb_{hash(full_url) % 999999}",
            })

        return results

    except Exception as e:
        logger.warning(f"[Kabum] Erro ao buscar '{query}': {e}")
        return []


def _scrape_html(model_name: str, query: str) -> list[dict]:
    """Fallback HTML scraping."""
    try:
        import re
        resp = requests.get(
            f"https://www.kabum.com.br/busca/{query.replace(' ', '-')}",
            headers={**HEADERS, "Accept": "text/html"},
            timeout=20,
        )
        if resp.status_code != 200:
            return []

        # Extrai preços do JSON embutido na página
        matches = re.findall(
            r'"dsc_nome"\s*:\s*"([^"]+)".*?"vlr_preco"\s*:\s*(\d+\.?\d*)',
            resp.text,
        )
        results = []
        for title, price_str in matches[:5]:
            if "iphone" not in title.lower():
                continue
            results.append({
                "store": "kabum",
                "model": model_name,
                "title": title,
                "price": float(price_str),
                "url": f"https://www.kabum.com.br/busca/{query.replace(' ', '-')}",
                "seller": "KaBuM!",
                "product_id": f"kb_{hash(title) % 999999}",
            })
        return results

    except Exception as e:
        logger.warning(f"[Kabum HTML] Erro: {e}")
        return []


def get_prices() -> list[dict]:
    results = []
    for model_name, query in IPHONE_QUERIES:
        items = _scrape_model(model_name, query)
        results.extend(items)
    logger.info(f"[Kabum] {len(results)} ofertas encontradas.")
    return results

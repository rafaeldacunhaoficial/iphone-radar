"""
Scraper Via Varejo Group — Casas Bahia e Ponto compartilham o mesmo backend.
"""
import logging
import re
import requests

logger = logging.getLogger(__name__)

IPHONE_QUERIES = [
    ("iPhone 17 Pro Max", "iphone-17-pro-max"),
    ("iPhone 17 Pro", "iphone-17-pro"),
    ("iPhone 17", "iphone-17"),
    ("iPhone 16 Pro Max", "iphone-16-pro-max"),
    ("iPhone 16 Pro", "iphone-16-pro"),
    ("iPhone 16", "iphone-16"),
    ("iPhone 15 Pro Max", "iphone-15-pro-max"),
    ("iPhone 15 Pro", "iphone-15-pro"),
    ("iPhone 15", "iphone-15"),
]

STORES = [
    ("casasbahia", "Casas Bahia", "casasbahia.com.br"),
    ("ponto", "Ponto", "ponto.com.br"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

BLACKLIST = ["capa", "pelicula", "case", "carregador", "capinha", "cabo", "fone", "suporte"]


def _scrape_store(model_name, query, store_id, store_name, domain):
    try:
        url = f"https://www.{domain}/busca/{query}/"
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
        patterns = [
            r'"productName"\s*:\s*"([^"]*(?:iPhone|iphone)[^"]*)"[^}]{0,300}?"bestPrice"\s*:\s*(\d+(?:\.\d+)?)',
            r'"name"\s*:\s*"([^"]*(?:iPhone|iphone)[^"]*)"[^}]{0,300}?"Price"\s*:\s*(\d+(?:\.\d+)?)',
        ]
        matches = []
        for pattern in patterns:
            matches = re.findall(pattern, resp.text, re.DOTALL)
            if matches:
                break
        results = []
        seen = set()
        for title, price_str in matches[:5]:
            if title in seen or any(w in title.lower() for w in BLACKLIST):
                continue
            try:
                price = float(price_str)
            except ValueError:
                continue
            if price < 500:
                continue
            seen.add(title)
            results.append({"store": store_id, "model": model_name, "title": title[:120],
                "price": price, "url": url, "seller": store_name,
                "product_id": f"{store_id}_{hash(title) % 999999}"})
        return results
    except Exception as e:
        logger.warning(f"[{store_name}] Erro: {e}")
        return []


def get_prices():
    results = []
    for model_name, query in IPHONE_QUERIES:
        for store_id, store_name, domain in STORES:
            results.extend(_scrape_store(model_name, query, store_id, store_name, domain))
    logger.info(f"[Via Varejo] {len(results)} ofertas encontradas.")
    return results

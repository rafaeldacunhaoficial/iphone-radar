"""
Scraper Magazine Luiza — extrai dados do __NEXT_DATA__ (SSR).
A página de busca renderiza os produtos no servidor, incluindo o JSON
completo no <script id="__NEXT_DATA__">.
"""
import json
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.magazineluiza.com.br/",
}

IPHONE_QUERIES = [
    ("iPhone 17 Pro Max", "iphone+17+pro+max"),
    ("iPhone 17 Pro",     "iphone+17+pro"),
    ("iPhone 17",         "iphone+17"),
    ("iPhone 16 Pro Max", "iphone+16+pro+max"),
    ("iPhone 16 Pro",     "iphone+16+pro"),
    ("iPhone 16",         "iphone+16"),
    ("iPhone 15 Pro Max", "iphone+15+pro+max"),
    ("iPhone 15 Pro",     "iphone+15+pro"),
    ("iPhone 15",         "iphone+15"),
]

BLACKLIST = ["capa", "película", "case", "carregador", "capinha", "cabo", "fone", "suporte"]


def _scrape_model(model_name: str, query: str) -> list[dict]:
    try:
        url = f"https://www.magazineluiza.com.br/busca/{query}/"
        resp = requests.get(url, headers=HEADERS, timeout=25)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        nd_tag = soup.find("script", id="__NEXT_DATA__")
        if not nd_tag:
            return []
        data = json.loads(nd_tag.string)
        products = (
            data.get("props", {}).get("pageProps", {})
                .get("data", {}).get("search", {}).get("products", [])
        )
        results = []
        seen = set()
        for p in products[:10]:
            title = p.get("title", "")
            if not title or title in seen or not "iphone" in title.lower(): continue
            if any(w in title.lower() for w in BLACKLIST): continue
            price_data = p.get("price", {})
            price = float(price_data.get("bestPrice") or price_data.get("price") or 0)
            if price < 500: continue
            path = p.get("path", "")
            product_url = f"https://www.magazineluiza.com.br{path}" if path else "https://www.magazineluiza.com.br"
            product_id = p.get("id") or p.get("variationId") or str(hash(title) % 999999)
            seen.add(title)
            results.append({"store": "magalu", "model": model_name, "title": title[:120],
                "price": price, "url": product_url,
                "seller": (p.get("seller") or {}).get("description", "Magazine Luiza"),
                "product_id": f"ml_{product_id}"})
        return results
    except Exception as e:
        logger.warning(f"[Magalu] Erro: {e}")
        return []


def get_prices() -> list[dict]:
    results = []
    seen_ids: set[str] = set()
    for model_name, query in IPHONE_QUERIES:
        for item in _scrape_model(model_name, query):
            if item["product_id"] not in seen_ids:
                seen_ids.add(item["product_id"])
                results.append(item)
    logger.info(f"[Magalu] {len(results)} ofertas encontradas.")
    return results

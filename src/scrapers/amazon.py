"""
Scraper Amazon BR — raspagem via search page com headers realistas.
A Amazon usa CloudFront/bot detection; o scraper captura o que for possível.
Se falhar, retorna lista vazia e registra o erro (não trava o sistema).
"""

import re
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.amazon.com.br/s"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.amazon.com.br/",
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


def _parse_price(text: str) -> Optional[float]:
    """Converte 'R$ 9.999,00' → 9999.00"""
    text = re.sub(r"[^\d,]", "", text.replace(".", ""))
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _scrape_model(model_name: str, query: str) -> list[dict]:
    try:
        resp = requests.get(
            SEARCH_URL,
            params={"k": query, "i": "electronics"},
            headers=HEADERS,
            timeout=20,
        )
        if resp.status_code != 200:
            logger.warning(f"[AMZ] Status {resp.status_code} para '{query}'")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        for card in soup.select('[data-component-type="s-search-result"]')[:5]:
            title_el = card.select_one("h2 a span")
            price_whole = card.select_one(".a-price-whole")
            price_frac = card.select_one(".a-price-fraction")
            link_el = card.select_one("h2 a")

            if not title_el or not price_whole:
                continue

            title = title_el.get_text(strip=True)
            price_str = price_whole.get_text(strip=True)
            if price_frac:
                price_str += "," + price_frac.get_text(strip=True)

            price = _parse_price(price_str)
            if not price or price < 500:
                continue

            href = link_el.get("href", "") if link_el else ""
            url = f"https://www.amazon.com.br{href.split('?')[0]}" if href else ""

            # Filtro básico de relevância
            title_lower = title.lower()
            if "iphone" not in title_lower:
                continue
            if any(w in title_lower for w in ["capa", "capinha", "película", "case", "carregador"]):
                continue

            results.append({
                "store": "amazon",
                "model": model_name,
                "title": title,
                "price": price,
                "url": url,
                "seller": "Amazon.com.br",
                "product_id": f"amz_{hash(url) % 999999}",
            })

        return results

    except Exception as e:
        logger.warning(f"[AMZ] Erro ao scraper '{query}': {e}")
        return []


from typing import Optional


def get_prices() -> list[dict]:
    results = []
    for model_name, query in IPHONE_QUERIES:
        items = _scrape_model(model_name, query)
        results.extend(items)
    logger.info(f"[AMZ] {len(results)} ofertas encontradas.")
    return results

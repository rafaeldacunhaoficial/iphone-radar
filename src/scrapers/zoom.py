"""
Scraper Zoom BR — maior agregador de preços do Brasil.
Monitorar o Zoom captura ofertas de centenas de lojas de uma só vez.
"""
import logging
import re
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.zoom.com.br/",
}

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

BLACKLIST = ["capa", "película", "case", "carregador", "capinha", "cabo", "fone", "suporte"]


def _scrape_model(model_name: str, query: str) -> list[dict]:
    try:
        url = f"https://www.zoom.com.br/celular/{query}"
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            # Tenta busca genérica
            url = f"https://www.zoom.com.br/search?q={query.replace('-', '+')}"
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        # Tenta extrair de JSON embutido (Next.js/SSR)
        json_matches = re.findall(
            r'"name"\s*:\s*"([^"]*(?:iPhone|iphone)[^"]*)"[^}]{0,500}?"price"\s*:\s*(\d+(?:\.\d+)?)',
            resp.text,
            re.DOTALL,
        )

        seen = set()
        for title, price_str in json_matches[:5]:
            if title in seen:
                continue
            if any(w in title.lower() for w in BLACKLIST):
                continue
            try:
                price = float(price_str)
            except ValueError:
                continue
            if price < 500:
                continue
            seen.add(title)
            results.append({
                "store": "zoom",
                "model": model_name,
                "title": title[:120],
                "price": price,
                "url": url,
                "seller": "Zoom (agregador)",
                "product_id": f"zoom_{hash(title) % 999999}",
            })

        # Fallback: parse HTML de cards
        if not results:
            for card in soup.select("[class*='product'], [class*='card'], article")[:5]:
                title_el = card.select_one("h2, h3, [class*='name'], [class*='title']")
                price_el = card.select_one("[class*='price'], [itemprop='price']")
                link_el = card.select_one("a[href]")
                if not title_el or not price_el:
                    continue
                title = title_el.get_text(strip=True)
                if "iphone" not in title.lower():
                    continue
                if any(w in title.lower() for w in BLACKLIST):
                    continue
                price_text = re.sub(r"[^\d]", "", price_el.get_text().replace(",", ""))
                try:
                    price = float(price_text) / 100
                except ValueError:
                    continue
                if price < 500:
                    continue
                href = link_el.get("href", "") if link_el else ""
                full_url = href if href.startswith("http") else f"https://www.zoom.com.br{href}"
                results.append({
                    "store": "zoom",
                    "model": model_name,
                    "title": title[:120],
                    "price": price,
                    "url": full_url,
                    "seller": "Zoom (agregador)",
                    "product_id": f"zoom_{hash(full_url) % 999999}",
                })

        return results

    except Exception as e:
        logger.warning(f"[Zoom] Erro ao buscar '{query}': {e}")
        return []


def get_prices() -> list[dict]:
    results = []
    for model_name, query in IPHONE_QUERIES:
        items = _scrape_model(model_name, query)
        results.extend(items)
    logger.info(f"[Zoom] {len(results)} ofertas encontradas.")
    return results

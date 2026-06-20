"""
Scraper MercadoLivre - scraping HTML da pagina de listagem (SSR).
A API oficial exige OAuth desde 2024.
"""
import re
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.mercadolivre.com.br/",
}

IPHONE_QUERIES = [
    ("iPhone 17 Pro Max", "iphone-17-pro-max"),
    ("iPhone 17 Pro",     "iphone-17-pro"),
    ("iPhone 17",         "iphone-17"),
    ("iPhone 16 Pro Max", "iphone-16-pro-max"),
    ("iPhone 16 Pro",     "iphone-16-pro"),
    ("iPhone 16",         "iphone-16"),
    ("iPhone 15 Pro Max", "iphone-15-pro-max"),
    ("iPhone 15 Pro",     "iphone-15-pro"),
    ("iPhone 15",         "iphone-15"),
]

BLACKLIST = ["capa", "capinha", "pelicula", "case", "carregador", "cabo",
             "fone", "airpods", "watch", "ipad", "suporte", "holder", "usado"]


def _parse_price(text: str) -> float:
    clean = re.sub(r"[^\d,]", "", text.replace(".", "")).replace(",", ".")
    try: return float(clean)
    except: return 0.0


def _scrape_model(model_name: str, slug: str) -> list[dict]:
    try:
        url = f"https://lista.mercadolivre.com.br/{slug}_NoIndex_True"
        resp = requests.get(url, headers=HEADERS, timeout=25)
        if resp.status_code != 200: return []
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        seen = set()
        cards = soup.select(".poly-card, .ui-search-result__wrapper, [class*='ui-search-layout__item']")
        for card in cards[:10]:
            title_el = card.select_one(".poly-component__title, .ui-search-item__title, [class*='title']")
            if not title_el: continue
            title = title_el.get_text(strip=True)
            if not title or title in seen or "iphone" not in title.lower(): continue
            if any(w in title.lower() for w in BLACKLIST): continue
            price_el = card.select_one(".andes-money-amount__fraction, .price-tag-amount, [class*='price']")
            if not price_el: continue
            price = _parse_price(price_el.get_text(strip=True))
            if price < 500: continue
            link_el = card.select_one("a[href]")
            link = (link_el.get("href", "") if link_el else "").split("?")[0] or f"https://lista.mercadolivre.com.br/{slug}"
            seen.add(title)
            results.append({"store": "mercadolivre", "model": model_name, "title": title[:120],
                "price": price, "url": link, "seller": "MercadoLivre",
                "product_id": f"ml_{abs(hash(link)) % 9999999}"})
        if not results:
            for m in re.finditer(r'"price"\s*:\s*(\d+\.?\d*)[^}]{0,200}"title"\s*:\s*"([^"]*iphone[^"]*)"', resp.text, re.IGNORECASE|re.DOTALL):
                price = float(m.group(1)); title = m.group(2)
                if price < 500 or title in seen: continue
                if any(w in title.lower() for w in BLACKLIST): continue
                seen.add(title)
                results.append({"store": "mercadolivre", "model": model_name, "title": title[:120],
                    "price": price, "url": f"https://lista.mercadolivre.com.br/{slug}",
                    "seller": "MercadoLivre", "product_id": f"ml_{abs(hash(title)) % 9999999}"})
                if len(results) >= 5: break
        return results[:5]
    except Exception as e:
        logger.warning(f"[ML] Erro: {e}")
        return []


def get_prices() -> list[dict]:
    results = []
    seen_ids = set()
    for model_name, slug in IPHONE_QUERIES:
        for item in _scrape_model(model_name, slug):
            if item["product_id"] not in seen_ids:
                seen_ids.add(item["product_id"])
                results.append(item)
    logger.info(f"[ML] {len(results)} ofertas encontradas.")
    return results

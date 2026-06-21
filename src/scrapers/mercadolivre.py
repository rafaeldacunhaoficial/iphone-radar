"""
Scraper MercadoLivre - extrai JSON-LD da pagina de busca.
Sem OAuth - usa HTML publico de lista.mercadolivre.com.br.
"""
import json
import logging
import re
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
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

BLACKLIST = [
    "capa","capinha","pelicula","case","carregador","cabo","fone",
    "airpods","watch","ipad","suporte","holder","recondicionado","seminovo","usado",
]


def _scrape_model(model_name, slug):
    try:
        url = f"https://lista.mercadolivre.com.br/{slug}"
        resp = requests.get(url, headers=HEADERS, timeout=25)
        if resp.status_code != 200:
            logger.warning(f"[ML] {slug} status {resp.status_code}")
            return []
        results = []
        seen = set()
        for match in re.finditer(
            r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
            resp.text, re.DOTALL
        ):
            try:
                data = json.loads(match.group(1))
                graph = data.get("@graph") or [data]
                for node in graph:
                    if node.get("@type") != "Product":
                        continue
                    name = node.get("name", "")
                    if not name or name in seen:
                        continue
                    if "iphone" not in name.lower():
                        continue
                    if any(w in name.lower() for w in BLACKLIST):
                        continue
                    offers = node.get("offers") or {}
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    try:
                        price = float(offers.get("price") or 0)
                    except (TypeError, ValueError):
                        continue
                    if price < 500:
                        continue
                    purl = offers.get("url") or node.get("url") or url
                    seller_info = offers.get("seller") or {}
                    seller = seller_info.get("name") if isinstance(seller_info, dict) else "MercadoLivre"
                    pid = abs(hash(purl)) % 9999999
                    seen.add(name)
                    results.append({
                        "store": "mercadolivre",
                        "model": model_name,
                        "title": name[:120],
                        "price": price,
                        "url": purl[:200],
                        "seller": seller or "MercadoLivre",
                        "product_id": f"ml_{pid}",
                    })
            except Exception:
                continue
        return results
    except Exception as e:
        logger.warning(f"[ML] {slug}: {e}")
        return []


def get_prices():
    results = []
    seen_ids = set()
    for mn, slug in IPHONE_QUERIES:
        for it in _scrape_model(mn, slug):
            if it["product_id"] not in seen_ids:
                seen_ids.add(it["product_id"])
                results.append(it)
    logger.info(f"[MercadoLivre] {len(results)} ofertas.")
    return results

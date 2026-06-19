"""
Scraper Apple Store BR — API oficial de produtos Apple no Brasil.
"""
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.apple.com/br/",
}

IPHONE_MODELS = [
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


def _fetch_model(model_name: str, slug: str) -> list[dict]:
    results = []
    # Tenta API JSON da Apple BR
    try:
        api_url = f"https://www.apple.com/br/shop/buy-iphone/{slug}"
        resp = requests.get(api_url, headers=HEADERS, timeout=20)
        # Se retornar JSON com produtos
        if resp.status_code == 200 and "application/json" in resp.headers.get("Content-Type", ""):
            data = resp.json()
            products = data.get("products", [])
            for p in products[:3]:
                price = p.get("currentPrice", {}).get("fullPrice", 0)
                if not price or price < 500:
                    continue
                title = p.get("familyType", model_name)
                results.append({
                    "store": "apple_store",
                    "model": model_name,
                    "title": title[:120],
                    "price": float(price),
                    "url": f"https://www.apple.com/br/shop/buy-iphone/{slug}",
                    "seller": "Apple Store",
                    "product_id": f"apple_{slug}_{hash(title) % 999999}",
                })
        # Fallback: parse HTML simples
        if not results and resp.status_code == 200:
            import re
            prices = re.findall(r'R\$\s*([\d\.]+,[\d]{2})', resp.text)
            for price_str in prices[:2]:
                try:
                    price = float(price_str.replace(".", "").replace(",", "."))
                    if price < 500:
                        continue
                    results.append({
                        "store": "apple_store",
                        "model": model_name,
                        "title": model_name,
                        "price": price,
                        "url": f"https://www.apple.com/br/shop/buy-iphone/{slug}",
                        "seller": "Apple Store",
                        "product_id": f"apple_{slug}_{int(price)}",
                    })
                    break
                except ValueError:
                    continue
    except Exception as e:
        logger.warning(f"[Apple Store] Erro em {model_name}: {e}")
    return results


def get_prices() -> list[dict]:
    results = []
    for model_name, slug in IPHONE_MODELS:
        results.extend(_fetch_model(model_name, slug))
    logger.info(f"[Apple Store] {len(results)} ofertas encontradas.")
    return results

"""Scraper Apple Store BR - parse JSON embutido nas paginas buy-iphone."""
import json
import logging
import re
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# Apple BR buy-iphone pages - each embeds all configs in a JSON script tag
BUY_IPHONE_URLS = [
    ("iPhone 17 Pro Max / Pro", "https://www.apple.com/br/shop/buy-iphone/iphone-17-pro"),
    ("iPhone 17 / Plus", "https://www.apple.com/br/shop/buy-iphone/iphone-17"),
    ("iPhone 16 / Plus", "https://www.apple.com/br/shop/buy-iphone/iphone-16"),
]

BASE_URL = "https://www.apple.com/br/shop/product"


def _extract_products(html: str, family_label: str) -> list:
    """Find the embedded JSON script with data.products and extract all items."""
    # The script tag is a plain JSON block (not application/ld+json)
    # It contains: {"data":{"products":[{"partNumber":"...","price":{"fullPrice":XXXX},"name":"..."}]}}
    pattern = re.compile(
        r'<script[^>]*>(\{\s*"config".*?"data".*?"products".*?\})</script>',
        re.DOTALL,
    )
    results = []
    for m in pattern.finditer(html):
        raw = m.group(1)
        try:
            d = json.loads(raw)
            products = d.get("data", {}).get("products", [])
            if not products:
                continue
            for p in products:
                name = p.get("name", "")
                part = p.get("partNumber", "")
                sku = p.get("sku", "")
                full_price = p.get("price", {}).get("fullPrice")
                if not name or not full_price or not part:
                    continue
                # Determine model from name
                model = name.split(" ")[0] + " " + name.split(" ")[1] if name else family_label
                if "Pro Max" in name:
                    model = "iPhone " + name.split("iPhone ")[-1].split(" ")[1] + " Pro Max"
                elif "Pro" in name:
                    model = "iPhone " + name.split("iPhone ")[-1].split(" ")[1] + " Pro"
                elif "Plus" in name:
                    model = "iPhone " + name.split("iPhone ")[-1].split(" ")[1] + " Plus"
                else:
                    model = "iPhone " + name.split("iPhone ")[-1].split(" ")[1]
                results.append({
                    "store": "apple_store",
                    "model": model,
                    "title": name[:120],
                    "price": float(full_price),
                    "url": f"{BASE_URL}/{sku}"[:200],
                    "seller": "Apple Store",
                    "product_id": f"apple_{part.replace('/', '_')}",
                })
            logger.info(f"[Apple] {family_label}: {len(results)} configs extraidos")
            return results
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"[Apple] parse error: {e}")
            continue
    return results


def get_prices() -> list:
    all_results = []
    debug = {}
    for family_label, url in BUY_IPHONE_URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            html = r.text
            logger.info(f"[Apple] {family_label}: status={r.status_code} size={len(html)}")
            if r.status_code != 200:
                debug[family_label] = {"status": r.status_code, "count": 0}
                continue
            items = _extract_products(html, family_label)
            all_results.extend(items)
            debug[family_label] = {"status": r.status_code, "size": len(html), "count": len(items)}
        except requests.RequestException as e:
            logger.error(f"[Apple] {family_label}: {e}")
            debug[family_label] = {"error": str(e), "count": 0}
    logger.info(f"[Apple] Total: {len(all_results)} produtos de {len(BUY_IPHONE_URLS)} paginas")
    get_prices._last_debug = debug
    return all_results

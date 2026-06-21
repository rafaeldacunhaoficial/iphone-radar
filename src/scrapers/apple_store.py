"""Scraper Apple Store BR - parse JSON embutido nas paginas buy-iphone."""
import json, logging, re, requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

BUY_IPHONE_URLS = [
    ("iPhone 17 Pro Max / Pro", "https://www.apple.com/br/shop/buy-iphone/iphone-17-pro"),
    ("iPhone 17 / Plus",        "https://www.apple.com/br/shop/buy-iphone/iphone-17"),
    ("iPhone 16 / Plus",        "https://www.apple.com/br/shop/buy-iphone/iphone-16"),
]
BASE_URL = "https://www.apple.com/br/shop/product"

_MODEL_RE = re.compile(r'(iPhone\s+\d+(?:\s+Pro\s+Max|\s+Pro|\s+Plus)?)')

def _extract_model(name, family_label):
    """Extract 'iPhone 17 Pro Max' from 'iPhone 17 Pro Max 512GB Deep Blue'."""
    m = _MODEL_RE.match(name)
    return m.group(1) if m else family_label

def _extract_products(html, family_label):
    """Find embedded JSON script with data.products and extract all items."""
    pattern = re.compile(
        r'<script[^>]*>(\{"config".*?"data".*?"products".*?\})</script>',
        re.DOTALL,
    )
    results = []
    seen = set()
    for m in pattern.finditer(html):
        try:
            d = json.loads(m.group(1))
            products = d.get("data", {}).get("products", [])
            for p in products:
                name = p.get("name", "")
                part = p.get("partNumber", "")
                sku = p.get("sku", "")
                full_price = p.get("price", {}).get("fullPrice")
                if not name or not full_price or not part:
                    continue
                if part in seen:
                    continue
                seen.add(part)
                model = _extract_model(name, family_label)
                results.append({
                    "store": "apple_store",
                    "model": model,
                    "title": name[:120],
                    "price": float(full_price),
                    "url": f"{BASE_URL}/{sku}"[:200],
                    "seller": "Apple Store",
                    "product_id": f"apple_{part.replace('/', '_')}",
                })
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.debug(f"[apple_store] parse error: {e}")
            continue
    return results

def get_prices():
    all_results = []
    debug = {}
    for family_label, url in BUY_IPHONE_URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            items = _extract_products(r.text, family_label) if r.status_code == 200 else []
            all_results.extend(items)
            debug[family_label] = {"status": r.status_code, "size": len(r.text), "count": len(items)}
            logger.info(f"[apple_store] {family_label}: {len(items)} produtos (HTTP {r.status_code})")
        except Exception as e:
            logger.error(f"[apple_store] {family_label}: erro {e}")
            debug[family_label] = {"status": None, "size": 0, "count": 0, "error": str(e)}
    get_prices._last_debug = debug
    return all_results

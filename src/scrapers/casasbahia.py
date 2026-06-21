"""Scraper Casas Bahia - categoria __NEXT_DATA__ + JSON-LD de produto."""
import json
import logging
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

CATEGORIES = [
    ("iPhone 17 Pro Max", "https://www.casasbahia.com.br/iphone-17-pro-max/b"),
    ("iPhone 17 Pro", "https://www.casasbahia.com.br/iphone-17-pro/b"),
    ("iPhone 17", "https://www.casasbahia.com.br/iphone-17/b"),
    ("iPhone 16 Pro Max", "https://www.casasbahia.com.br/iphone-16-pro-max/b"),
    ("iPhone 16 Pro", "https://www.casasbahia.com.br/iphone-16-pro/b"),
    ("iPhone 16", "https://www.casasbahia.com.br/iphone-16/b"),
    ("iPhone 15 Pro Max", "https://www.casasbahia.com.br/iphone-15-pro-max/b"),
    ("iPhone 15 Pro", "https://www.casasbahia.com.br/iphone-15-pro/b"),
    ("iPhone 15", "https://www.casasbahia.com.br/iphone-15/b"),
]

BLACKLIST = [
    "capa", "capinha", "pelicula", "película", "case", "carregador",
    "cabo", "fone", "airpods", "watch", "ipad", "suporte", "holder",
    "recondicionado", "seminovo", "usado", "protetor",
]

MAX_PER_CATEGORY = 12
MAX_WORKERS = 5
MIN_HTML_SIZE = 50_000  # Below this = Cloudflare challenge page


def _is_blacklisted(title: str) -> bool:
    return any(w in title.lower() for w in BLACKLIST)


def _extract_hrefs(html: str) -> list:
    """Parse __NEXT_DATA__ from category page to get product hrefs + titles."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
        products = (
            data.get("props", {})
            .get("pageProps", {})
            .get("initialState", {})
            .get("search", {})
            .get("results", {})
            .get("products", [])
        )
        result = []
        for p in products:
            href = p.get("href", "")
            title = p.get("title", "")
            if href and title and not _is_blacklisted(title):
                result.append((href, title))
        return result[:MAX_PER_CATEGORY]
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def _fetch_product_price(url: str, title: str) -> dict | None:
    """Fetch single product page, extract JSON-LD price."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            return None
        for m in re.finditer(
            r'<script[^>]+type=["\'\']application/ld\+json["\'\'][^>]*>(.*?)</script>',
            r.text, re.DOTALL | re.IGNORECASE,
        ):
            try:
                d = json.loads(m.group(1))
                if d.get("@type") != "Product":
                    continue
                offers = d.get("offers", [])
                if isinstance(offers, dict):
                    offers = [offers]
                for offer in offers:
                    price = offer.get("price")
                    if price:
                        sku = url.split("/p/")[-1].split("/")[0]
                        return {
                            "store": "casasbahia",
                            "model": "",
                            "title": (d.get("name") or title)[:120],
                            "price": float(price),
                            "url": url[:200],
                            "seller": "Casas Bahia",
                            "product_id": f"cb_{sku}",
                        }
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
    except requests.RequestException:
        pass
    return None


def _scrape_category(model_name: str, category_url: str) -> tuple:
    debug = {
        "url": category_url,
        "status": None,
        "html_size": 0,
        "hrefs_found": 0,
        "prices_found": 0,
        "error": None,
    }
    results = []
    try:
        r = requests.get(category_url, headers=HEADERS, timeout=30)
        debug["status"] = r.status_code
        debug["html_size"] = len(r.text)
        if r.status_code != 200:
            debug["error"] = f"HTTP {r.status_code}"
            return results, debug
        if len(r.text) < MIN_HTML_SIZE:
            debug["error"] = f"Page too small ({len(r.text)}B) — Cloudflare challenge?"
            return results, debug
        hrefs = _extract_hrefs(r.text)
        debug["hrefs_found"] = len(hrefs)
        if not hrefs:
            return results, debug
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(_fetch_product_price, href, title): (href, title)
                for href, title in hrefs
            }
            for future in as_completed(futures):
                item = future.result()
                if item:
                    item["model"] = model_name
                    results.append(item)
        debug["prices_found"] = len(results)
    except requests.RequestException as e:
        debug["error"] = str(e)
        logger.error(f"[CB] {model_name}: {e}")
    logger.info(
        f"[CB] {model_name}: status={debug['status']} "
        f"size={debug['html_size']} hrefs={debug['hrefs_found']} "
        f"prices={debug['prices_found']}"
    )
    return results, debug


def get_prices() -> list:
    all_results = []
    all_debug = {}
    for model_name, category_url in CATEGORIES:
        items, dbg = _scrape_category(model_name, category_url)
        all_results.extend(items)
        all_debug[model_name] = dbg
    logger.info(f"[CB] Total: {len(all_results)} itens")
    get_prices._last_debug = all_debug
    return all_results

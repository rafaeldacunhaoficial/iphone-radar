"""Scraper MercadoLivre - JSON-LD da pagina de busca. Sem OAuth."""
import json
import logging
import re
import requests

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

BLACKLIST = [
    "capa", "capinha", "pelicula", "película", "case", "carregador",
    "cabo", "fone", "airpods", "watch", "ipad", "suporte", "holder",
    "recondicionado", "seminovo", "usado", "protetor",
]


def _is_blacklisted(title: str) -> bool:
    t = title.lower()
    return any(w in t for w in BLACKLIST)


def _extract_pid(url: str) -> str:
    m = re.search(r"/p/(MLB\d+)", url)
    if m:
        return m.group(1)
    m = re.search(r"MLB[-_]?(\d+)", url)
    if m:
        return "MLB" + m.group(1)
    return "ml_" + str(abs(hash(url)) % 10 ** 8)


def _scrape_model(model_name: str, slug: str) -> tuple:
    """Returns (results_list, debug_dict)."""
    url = f"https://lista.mercadolivre.com.br/{slug}"
    debug = {
        "url": url,
        "status": None,
        "html_size": 0,
        "jsonld_blocks": 0,
        "product_nodes": 0,
        "after_filter": 0,
        "error": None,
    }
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        debug["status"] = resp.status_code
        debug["html_size"] = len(resp.text)
        if resp.status_code != 200:
            debug["error"] = f"HTTP {resp.status_code}"
            return results, debug
        html = resp.text
        pattern = re.compile(
            r'<script[^>]+type=["\'\']application/ld\+json["\'\'][^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            raw = match.group(1).strip()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            debug["jsonld_blocks"] += 1
            graph = data.get("@graph") or [data]
            for node in graph:
                if node.get("@type") != "Product":
                    continue
                debug["product_nodes"] += 1
                name = node.get("name", "")
                if not name or _is_blacklisted(name):
                    continue
                offers = node.get("offers", {})
                if isinstance(offers, list):
                    offer = offers[0] if offers else {}
                else:
                    offer = offers
                price = offer.get("price")
                purl = offer.get("url", "")
                if not price or not purl:
                    continue
                try:
                    price = float(price)
                except (TypeError, ValueError):
                    continue
                if price < 1000:
                    continue
                pid = _extract_pid(purl)
                results.append({
                    "store": "mercadolivre",
                    "model": model_name,
                    "title": name[:120],
                    "price": price,
                    "url": purl[:200],
                    "seller": "MercadoLivre",
                    "product_id": pid,
                })
        debug["after_filter"] = len(results)
    except requests.RequestException as e:
        debug["error"] = str(e)
        logger.error(f"[ML] {slug}: {e}")
    logger.info(
        f"[ML] {slug}: status={debug['status']} "
        f"size={debug['html_size']} "
        f"blocks={debug['jsonld_blocks']} "
        f"products={debug['product_nodes']} "
        f"results={debug['after_filter']}"
    )
    return results, debug


def get_prices() -> list:
    all_results = []
    all_debug = {}
    for model_name, slug in IPHONE_QUERIES:
        items, dbg = _scrape_model(model_name, slug)
        all_results.extend(items)
        all_debug[slug] = dbg
    logger.info(f"[ML] Total: {len(all_results)} itens de {len(IPHONE_QUERIES)} queries")
    # Attach debug for main.py to pick up
    get_prices._last_debug = all_debug
    return all_results

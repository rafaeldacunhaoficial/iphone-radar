"""Scraper Go Imports - Apple reseller (HTML estatico, BeautifulSoup)."""
import logging
import re
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

MODEL_URLS = [
    ("iPhone 17 Pro Max", "https://www.goimports.com.br/iphoness/iPhone-17-Pro-Max"),
    ("iPhone 17 Pro",     "https://www.goimports.com.br/iphoness/iPhone-17-Pro"),
    ("iPhone 17",         "https://www.goimports.com.br/iphoness/iPhone-17"),
    ("iPhone 16",         "https://www.goimports.com.br/iphoness/iPhone-16"),
]

BLACKLIST = [
    "capa", "capinha", "pelicula", "case", "carregador", "cabo", "fone",
    "airpods", "watch", "ipad", "suporte", "kit", "acessorios",
    "protetor", "holder", "recondicionado", "seminovo", "usado", "gan", "hprime",
]


def _parse_price(text):
    cleaned = re.sub(r"[^\d,]", "", text).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _is_blacklisted(name):
    n = name.lower()
    return any(b in n for b in BLACKLIST)


def _scrape_model(model_name, url):
    debug = {"url": url, "status": None, "count": 0, "error": None}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        debug["status"] = resp.status_code
        if resp.status_code != 200:
            debug["error"] = f"HTTP {resp.status_code}"
            return [], debug
        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        seen = set()
        for price_el in soup.select(".price-new"):
            price_text = price_el.get_text(strip=True)
            price = _parse_price(price_text)
            if price < 1000:
                continue
            container = price_el.parent
            name_el = None
            link_el = None
            for _ in range(8):
                if container is None:
                    break
                name_el = container.find(["h2", "h3", "h4"])
                link_el = container.find("a", href=True)
                if name_el and link_el:
                    break
                container = container.parent
            if not name_el:
                continue
            name = name_el.get_text(strip=True)
            if not name or _is_blacklisted(name):
                continue
            href = link_el["href"] if link_el else url
            if not href.startswith("http"):
                href = "https://www.goimports.com.br" + href
            pid = "gi_" + re.sub(r"[^a-z0-9]", "_", name.lower())[:40]
            if pid in seen:
                continue
            seen.add(pid)
            results.append({
                "store": "goimports",
                "model": model_name,
                "title": name[:120],
                "price": price,
                "url": href[:200],
                "seller": "Go Imports",
                "product_id": pid,
            })
        debug["count"] = len(results)
        return results, debug
    except Exception as exc:
        debug["error"] = str(exc)[:120]
        logger.warning("[GoImports] %s: %s", url, exc)
        return [], debug


def get_prices():
    all_results = []
    all_debug = {}
    seen_ids = set()
    for model_name, url in MODEL_URLS:
        items, dbg = _scrape_model(model_name, url)
        all_debug[model_name] = dbg
        for item in items:
            if item["product_id"] not in seen_ids:
                seen_ids.add(item["product_id"])
                all_results.append(item)
    get_prices._last_debug = all_debug
    logger.info("[GoImports] %d ofertas.", len(all_results))
    return all_results

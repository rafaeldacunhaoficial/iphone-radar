"""Scraper Claro Loja - operadora Apple reseller (SSR Next.js __NEXT_DATA__)."""
import json
import logging
import re

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

URL = "https://www.claro.com.br/smartphones/apple"

# iPhone model: must contain "iPhone" followed by a model number
IPHONE_MODEL_RE = re.compile(r"iPhone\s+\d+", re.IGNORECASE)
# Blacklist accessories
BLACKLIST_RE = re.compile(r"(carregador|cabo|fone|airpod|watch|ipad|suporte|protetor|recondicionado|compatível|capa)", re.IGNORECASE)

def _parse_price(text: str) -> float:
    cleaned = re.sub(r"[^\d,]", "", text).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def _find_products(obj, depth: int = 0, results: list = None) -> list:
    if results is None:
        results = []
    if depth > 20 or not obj:
        return results

    if isinstance(obj, dict):
        iphone_name = None
        price_str = None

        for key, val in obj.items():
            if isinstance(val, str) and IPHONE_MODEL_RE.search(val) and not BLACKLIST_RE.search(val) and len(val) < 100:
                iphone_name = val
            if (key == "price" and isinstance(val, dict)
                    and isinstance(val.get("price"), str)
                    and "R$" in val["price"]):
                price_str = val["price"]

        if iphone_name and price_str:
            results.append({"name": iphone_name, "price": price_str})

        for v in obj.values():
            if isinstance(v, (dict, list)):
                _find_products(v, depth + 1, results)

    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                _find_products(item, depth + 1, results)

    return results


def get_prices() -> list:
    try:
        r = requests.get(URL, headers=HEADERS, timeout=20)
        r.raise_for_status()
    except Exception as exc:
        logging.error(f"[claro] request error: {exc}")
        get_prices._last_debug = {"error": str(exc)}
        return []

    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', r.text, re.DOTALL)
    if not m:
        get_prices._last_debug = {"error": "__NEXT_DATA__ not found", "html_size": len(r.text)}
        return []

    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as exc:
        get_prices._last_debug = {"error": str(exc)}
        return []

    dc = data.get("props", {}).get("pageProps", {}).get("dynamicComponents", {})
    raw_products = _find_products(dc)

    results = []
    seen: set = set()
    for p in raw_products:
        name = p["name"].strip()
        price = _parse_price(p["price"])
        if price <= 0 or name in seen:
            continue
        seen.add(name)
        results.append({"store": "claro", "model": name, "price": price})

    get_prices._last_debug = {
        "count": len(results),
        "products": [r["model"] + " R$" + str(r["price"]) for r in results],
        "html_size": len(r.text)
    }
    logging.info(f"[claro] {len(results)} produto(s)")
    return results

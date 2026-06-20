"""
Scraper KaBuM — usa o endpoint de busca SSR.
"""
import re
import json
import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://www.kabum.com.br/",
}

IPHONE_QUERIES = [
    ("iPhone 16 Pro Max", "iphone-16-pro-max"),
    ("iPhone 16 Pro",     "iphone-16-pro"),
    ("iPhone 16",         "iphone-16"),
    ("iPhone 15 Pro Max", "iphone-15-pro-max"),
    ("iPhone 15 Pro",     "iphone-15-pro"),
    ("iPhone 15",         "iphone-15"),
]

BLACKLIST = ["capa", "película", "case", "carregador", "capinha", "cabo", "fone", "suporte"]


def _scrape_model(model_name, slug):
    try:
        url = f"https://www.kabum.com.br/busca/{slug}"
        resp = requests.get(url, headers=HEADERS, timeout=25)
        if resp.status_code != 200: return []
        soup = BeautifulSoup(resp.text, "html.parser")
        nd_tag = soup.find("script", id="__NEXT_DATA__")
        if nd_tag:
            str_data = json.dumps(json.loads(nd_tag.string))
            matches = re.findall(r'"dsc_nome"\s*:\s*"([^"]+)"[^}]{0,300}"vlr_preco"\s*:\s*"?(\d+\.?\d*)"?[^}]{0,200}"url_link"\s*:\s*"([^"]+)"', str_data)
            results = []; seen = set()
            for title, price_str, link in matches[:8]:
                if title in seen or not "iphone" in title.lower(): continue
                if any(w in title.lower() for w in BLACKLIST): continue
                price = float(price_str)
                if price < 500: continue
                seen.add(title)
                full_url = link if link.startswith("http") else f"https://www.kabum.com.br{link}"
                results.append({"store": "kabum", "model": model_name, "title": title[:120],
                    "price": price, "url": full_url, "seller": "KaBuM!",
                    "product_id": f"kb_{abs(hash(full_url)) % 9999999}"})
            if results: return results
        matches = re.findall(r'dsc_nome["\s:]+([^"]*iphone[^"]*)["\s,]*[^}]*vlr_preco["\s;]+["\']?(\d+\.?\d*)', resp.text, re.IGNORECASE)
        results = []; seen = set()
        for title, price_str in matches[:5]:
            if title in seen or any(w in title.lower() for w in BLACKLIST): continue
            price = float(price_str)
            if price < 500: continue
            seen.add(title)
            results.append({"store": "kabum", "model": model_name, "title": title[:120],
                "price": price, "url": url, "seller": "KaBuM!",
                "product_id": f"kb_{abs(hash(title)) % 9999999}"})
        return results
    except: return []


def get_prices():
    results = []; seen_ids = set()
    for model_name, slug in IPHONE_QUERIES:
        for item in _scrape_model(model_name, slug):
            if item["product_id"] not in seen_ids:
                seen_ids.add(item["product_id"]); results.append(item)
    return results

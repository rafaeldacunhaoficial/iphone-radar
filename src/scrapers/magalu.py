"""
Scraper Magazine Luiza - extrai __NEXT_DATA__ com sessao para cookies.
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

BLACKLIST = ["capa","capinha","pelicula","case","carregador","cabo","fone","airpods","watch","ipad","suporte","holder","recondicionado","seminovo","usado"]


def _extract_price(p):
    for pf in ["bestPrice", "salesPrice", "price", "salePrice", "sellingPrice", "lowPrice"]:
        try:
            v = p.get(pf) or (p.get("price_data") or {}).get(pf) or (p.get("priceData") or {}).get(pf)
            if v:
                return float(v)
        except Exception:
            pass
    for key in ["price", "prices"]:
        try:
            sub = p.get(key)
            if isinstance(sub, dict):
                for pf in ["bestPrice", "salesPrice", "price", "salePrice", "sellingPrice", "lowPrice"]:
                    if sub.get(pf):
                        return float(sub[pf])
        except Exception:
            pass
    return 0


def _scrape_model(model_name, slug):
    try:
        session = requests.Session()
        session.get("https://www.magazineluiza.com.br/", headers=HEADERS, timeout=15)
        url = f"https://www.magazineluiza.com.br/busca/{slug}/"
        resp = session.get(url, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text, re.DOTALL)
        if not m:
            return []
        data = json.loads(m.group(1))
        products = None
        try:
            products = data["props"]["pageProps"]["data"]["search"]["products"]
        except Exception:
            pass
        if not products:
            try:
                ent = data["props"]["pageProps"]["initialState"]["entities"]["products"]
                products = list(ent.values()) if isinstance(ent, dict) else ent
            except Exception:
                pass
        if not products:
            return []
        results = []
        seen = set()
        for p in (products or [])[:15]:
            title = p.get("title") or p.get("description") or p.get("name") or p.get("productName") or ""
            if not title or title in seen or "iphone" not in title.lower():
                continue
            if any(w in title.lower() for w in BLACKLIST):
                continue
            price = _extract_price(p)
            if price < 500:
                continue
            pid = p.get("id") or p.get("productId") or abs(hash(title)) % 9999999
            purl = p.get("url") or p.get("link") or f"https://www.magazineluiza.com.br/busca/{slug}/"
            if not purl.startswith("http"):
                purl = "https://www.magazineluiza.com.br" + purl
            seller = p.get("seller")
            seller_name = seller.get("name") if isinstance(seller, dict) else (seller or "Magalu")
            seen.add(title)
            results.append({
                "store": "magalu",
                "model": model_name,
                "title": title[:120],
                "price": price,
                "url": purl,
                "seller": seller_name or "Magalu",
                "product_id": f"ml2_{pid}",
            })
        return results
    except Exception as e:
        logger.warning(f"[Magalu] {slug}: {e}")
        return []


def get_prices():
    results = []
    seen_ids = set()
    for mn, slug in IPHONE_QUERIES:
        for it in _scrape_model(mn, slug):
            if it["product_id"] not in seen_ids:
                seen_ids.add(it["product_id"])
                results.append(it)
    logger.info(f"[Magalu] {len(results)} ofertas.")
    return results

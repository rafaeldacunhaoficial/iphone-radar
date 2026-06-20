"""
Scraper KaBuM! - tenta API interna, depois __NEXT_DATA__ SSR.
"""
import json
import logging
import re
import requests

logger = logging.getLogger(__name__)

HEADERS_API = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.kabum.com.br/",
    "Origin": "https://www.kabum.com.br",
}

HEADERS_HTML = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (HTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pm;q=0.9",
}

IPHONE_QUERIES = [
    ("iPhone 17 Pro Max", "iphone 17 pro max", "iphone-17-pro-max"),
    ("iPhone 17 Pro",     "iphone 17 pro",     "iphone-17-pro"),
    ("iPhone 17",         "iphone 17",         "iphone-17"),
    ("iPhone 16 Pro Max", "iphone 16 pro max", "iphone-16-pro-max"),
    ("iPhone 16 Pro",     "iphone 16 pro",     "iphone-16-pro"),
    ("iPhone 16",         "iphone 16",         "iphone-16"),
    ("iPhone 15 Pro Max", "iphone 15 pro max", "iphone-15-pro-max"),
    ("iPhone 15 Pro",     "iphone 15 pro",     "iphone-15-pro"),
    ("iPhone 15",         "iphone 15",         "iphone-15"),
]

BLACKLIST = ["capa","capinha","pelicula","case","carregador","cabo","fone","airpods","watch","ipad","suporte","holder","recondicionado","seminovo","usado"]

def _try_api(model_name, query):
    try:
        resp = requests.get(
            "https://www.kabum.com.br/api/produto/busca",
            params={"q": query, "page_number": 1, "page_size": 20, "sort": 2},
            headers=HEADERS_API, timeout=20
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        items = data.get("data") or data.get("items") or data.get("products") or []
        results = []; seen = set()
        for p in items[:15]:
            title = p.get("dsc_nome") or p.get("name") or p.get("title") or ""
            if not title or title in seen or "iphone" not in title.lower():
                continue
            if any(w in title.lower() for w in BLACKLIST):
                continue
            price = 0
            for pf in ["vlr_preco","price","salePrice","bestPrice"]:
                try:
                    v = p.get(pf)
                    if v:
                        price = float(v); break
                except Exception:
                    pass
            if price < 500:
                continue
            pid = p.get("cod_produto") or p.get("id") or abs(hash(title)) % 9999999
            slug = p.get("url_link") or p.get("url") or str(pid)
            url = f"https://www.kabum.com.br/produto/{slug}" if not slug.startswith("http") else slug
            seen.add(title)
            results.append({"store":"kabum","model":model_name,"title":title[:120],"price":price,"url":url,"seller":"KaBuM","product_id":f"kb_{pid}"})
        return results
    except Exception as e:
        logger.warning(f"[KaBuM] API: {e}")
        return []

def _try_nextdata(model_name, slug):
    try:
        url = f"https://www.kabum.com.br/busca/{slug}"
        resp = requests.get(url, headers=HEADERS_HTML, timeout=20)
        if resp.status_code != 200:
            return []
        html = resp.text
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if not m:
            # fallback raw regex for price+name
            prices = re.findall(r'"vlr_preco"\s*:\s*([\d.]+)', html)
            names = re.findall(r'"dsc_nome"\s*:\s*"([^"]+)"', html)
            if prices and names:
                results = []
                for title, price_str in zip(names, prices):
                    if "iphone" not in title.lower():
                        continue
                    if any(w in title.lower() for w in BLACKLIST):
                        continue
                    price = float(price_str)
                    if price < 500:
                        continue
                    results.append({"store":"kabum","model":model_name,"title":title[:120],"price":price,"url":url,"seller":"KaBuM","product_id":f"kb_{abs(hash(title))%9999999}"})
                return results
            return []
        data = json.loads(m.group(1))
        # walk props to find product list
        products = None
        try:
            products = data["props"]["pageProps"]["data"]["listing"]["products"]
        except Exception:
            pass
        if not products:
            try:
                products = data["props"]["pageProps"]["initialState"]["catalog"]["products"]
            except Exception:
                pass
        if not products:
            return []
        results = []; seen = set()
        for p in products[:15]:
            title = p.get("dsc_nome") or p.get("name") or p.get("title") or ""
            if not title or title in seen or "iphone" not in title.lower():
                continue
            if any(w in title.lower() for w in BLACKLIST):
                continue
            price = 0
            for pf in ["vlr_preco","price","salePrice","bestPrice"]:
                try:
                    v = p.get(pf)
                    if v:
                        price = float(v); break
                except Exception:
                    pass
            if price < 500:
                continue
            pid = p.get("cod_produto") or p.get("id") or abs(hash(title)) % 9999999
            purl = p.get("url_link") or p.get("url") or url
            if purl and not purl.startswith("http"):
                purl = "https://www.kabum.com.br" + purl
            seen.add(title)
            results.append({"store":"kabum","model":model_name,"title":title[:120],"price":price,"url":purl or url,"seller":"KaBuM","product_id":f"kb_{pid}"})
        return results
    except Exception as e:
        logger.warning(f"[KaBuM] SSR {slug}: {e}")
        return []

def get_prices():
    results = []; seen_ids = set()
    for mn, q, slug in IPHONE_QUERIES:
        items = _try_api(mn, q)
        if not items:
            items = _try_nextdata(mn, slug)
        for it in items:
            if it["product_id"] not in seen_ids:
                seen_ids.add(it["product_id"]); results.append(it)
    logger.info(f"[KaBuM] {len(results)} ofertas.")
    return results

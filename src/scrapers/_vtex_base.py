"""
Base VTEX - 3 estrategias de endpoint: IS Shelf, Catalog API, IS Legacy GraphQL.
Usado por: casas_bahia (fallback), fastshop, iplace, extra, carrefour, fnac.
"""
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

IPHONE_QUERIES = [
    ("iPhone 17 Pro Max", "iphone 17 pro max"),
    ("iPhone 17 Pro",     "iphone 17 pro"),
    ("iPhone 17",         "iphone 17"),
    ("iPhone 16 Pro Max", "iphone 16 pro max"),
    ("iPhone 16 Pro",     "iphone 16 pro"),
    ("iPhone 16",         "iphone 16"),
    ("iPhone 15 Pro Max", "iphone 15 pro max"),
    ("iPhone 15 Pro",     "iphone 15 pro"),
    ("iPhone 15",         "iphone 15"),
]

BLACKLIST = ["capa","capinha","pelicula","case","carregador","cabo","fone","airpods","watch","ipad","suporte","holder","recondicionado","seminovo","usado"]

def _parse_vtex_items(products, store_id, display_name):
    results = []; seen = set()
    for p in products[:15]:
        title = (p.get("productName") or p.get("name") or p.get("title") or "")
        if not title or title in seen or "iphone" not in title.lower():
            continue
        if any(w in title.lower() for w in BLACKLIST):
            continue
        price = 0
        # VTEX nested: items[0].sellers[0].commertialOffer.Price
        try:
            for item in p.get("items", [])[:3]:
                for seller in item.get("sellers", [])[:2]:
                    offer = seller.get("commertialOffer", {})
                    p2 = offer.get("Price") or offer.get("ListPrice") or 0
                    if float(p2) > 500:
                        price = float(p2)
                        break
                if price:
                    break
        except Exception:
            pass
        if not price:
            for pf in ["price","salePrice","salesPrice","bestPrice","lowPrice","sellingPrice","Price"]:
                try:
                    v = p.get(pf)
                    if v and float(v) > 500:
                        price = float(v); break
                except Exception:
                    pass
        if price < 500:
            continue
        pid = p.get("productId") or p.get("id") or abs(hash(title)) % 9999999
        link_text = p.get("linkText") or p.get("slug") or str(pid)
        url = p.get("link") or p.get("url") or f"https://www.{store_id}.com.br/{link_text}/p"
        if url and not url.startswith("http"):
            url = "https://www." + store_id + ".com.br" + url
        seen.add(title)
        results.append({"store":store_id,"model":"iPhone","title":title[:120],"price":price,"url":url,"seller":display_name,"product_id":f"vtex_{store_id}_{pid}"})
    return results

def _try_is_shelf(base_url, store_id, model_name, query):
    try:
        url = f"{base_url}/_v/api/intelligent-search/product_search/shelf"
        params = {"query": query, "count": 20, "locale": "pt-BR", "hideUnavailableItems": "true", "selectedFacets": ""}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
        data = resp.json()
        products = data.get("products") or []
        return products
    except Exception as e:
        logger.debug(f"[VTEX IS Shelf] {store_id}: {e}")
        return []

def _try_catalog(base_url, store_id, model_name, query):
    try:
        url = f"{base_url}/api/catalog_system/pub/products/search/"
        params = {"_q": query, "_from": 0, "_to": 9, "O": "OrderByBestDiscountDESC"}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=20)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.debug(f"[VTEX Catalog] {store_id}: {e}")
        return []

def _try_is_legacy(base_url, store_id, model_name, query):
    try:
        gql = """
        query($q:String!){productSearch(query:$q,count:10,hideUnavailableItems:true){
          products{productId productName linkText items{sellers{commertialOffer{Price}}}}
        }}
        """
        url = f"{base_url}/_v/segment/graphql/v1"
        params = {"workspace": "master", "maxAge": "short", "appsEtag": "remove", "domain": "store", "locale": "pt-BR", "__bindingId": "any"}
        body = {"query": gql, "variables": {"q": query}}
        resp = requests.post(url, json=body, params=params, headers={**HEADERS, "Content-Type": "application/json"}, timeout=20)
        if resp.status_code != 200:
            return []
        data = resp.json()
        ps = (data.get("data") or {}).get("productSearch") or {}
        return ps.get("products") or []
    except Exception as e:
        logger.debug(f"[VTEX IS Legacy] {store_id}: {e}")
        return []

def scrape_vtex_store(base_url, store_id, display_name):
    all_results = []
    for model_name, query in IPHONE_QUERIES:
        products = (_try_is_shelf(base_url, store_id, model_name, query)
                    or _try_catalog(base_url, store_id, model_name, query)
                    or _try_is_legacy(base_url, store_id, model_name, query))
        if products:
            items = _parse_vtex_items(products, store_id, display_name)
            for it in items:
                it["model"] = model_name
            all_results.extend(items)
    # dedup
    seen = set(); out = []
    for it in all_results:
        if it["product_id"] not in seen:
            seen.add(it["product_id"]); out.append(it)
    logger.info(f"[VTEX:{display_name}] {len(out)} ofertas.")
    return out

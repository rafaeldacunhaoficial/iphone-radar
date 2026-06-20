"""
Scraper Shopee Brasil - API interna de busca.
"""
import logging
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://shopee.com.br/",
    "X-Requested-With": "XMLHttpRequest",
    "X-API-Source": "pc",
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

def _scrape_model(model_name,query):
    try:
        resp=requests.get("https://shopee.com.br/api/v4/search/search_items",params={"by":"relevancy","keyword":query,"limit":30,"newest":0,"order":"desc","page_type":"search","scenario":"PAGE_GLOBAL_SEARCH","version":2},headers=HEADERS,ttimeout=20)
        if resp.status_code!=200:return []
        results=[];seen=set()
        for entry in (resp.json().get("items") or [])[:15]:
            item=entry.get("item_basic",{})
            title=item.get("name","")
            if not title or title in seen or not "iphone" in title.lower():continue
            if any(w in title.lower() for w in BLACKLIST):continue
            price=(item.get("price") or item.get("price_min") or 0)/100000
            if price<500:continue
            id=item.get("itemid","");sid=item.get("shopid","")
            seen.add(title)
            results.append({"store":"shopee","model":model_name,"title":title[:120],"price":round(price,2),url":f"https://shopee.com.br/product/{sid}/{id}","seller":item.get("shop_name","Shopee"),"product_id":f"sp_{id}"})
        return results
    except Exception as e:logger.warning(f"[Shopee] {e}");return []

def get_prices():
    results=[];seen_ids=set()
    for mn,q in IPHONE_QUERIES:
        for it in _scrape_model(mn,q):
            if it["product_id"] not in seen_ids:seen_ids.add(it["product_id"]);results.append(it)
    logger.info(f"[Shopee] {len(results)} ofertas.")
    return results

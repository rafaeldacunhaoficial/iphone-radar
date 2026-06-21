"""
HTTP helper com bypass de Cloudflare.
Estrategia: cloudscraper (gratis) → ScraperAPI (pago, opcional via SCRAPER_API_KEY).
"""
import logging
import os
from urllib.parse import urlencode, quote

import requests as _requests

logger = logging.getLogger(__name__)

SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "").strip()

_cs = None  # cloudscraper instance (lazy init)


def _get_scraper():
    global _cs
    if _cs is None:
        try:
            import cloudscraper
            _cs = cloudscraper.create_scraper(
                browser={"browser": "chrome", "platform": "windows", "mobile": False}
            )
            logger.debug("[_http] cloudscraper iniciado")
        except Exception as e:
            logger.warning(f"[_http] cloudscraper indisponivel: {e}")
            _cs = False
    return _cs if _cs else None


def _looks_like_json(r):
    """True se resposta parece JSON valido (nao HTML de challenge)."""
    ct = r.headers.get("Content-Type", "")
    if "text/html" in ct:
        return False
    try:
        r.json()
        return True
    except Exception:
        return False


def _sapi_url(target, params=None):
    if params:
        sep = "&" if "?" in target else "?"
        target = target + sep + urlencode(params)
    return f"https://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={quote(target, safe=':/?=&%')}&country_code=br"


def get(url, *, headers=None, params=None, timeout=20):
    """GET: cloudscraper → ScraperAPI → requests puro."""
    # 1. cloudscraper
    cs = _get_scraper()
    if cs:
        try:
            r = cs.get(url, headers=headers, params=params, timeout=timeout)
            if r.status_code == 200 and _looks_like_json(r):
                logger.debug(f"[cs:GET] OK {url}")
                return r
            logger.debug(f"[cs:GET] status={r.status_code} {url}")
        except Exception as e:
            logger.debug(f"[cs:GET] excecao: {e}")

    # 2. ScraperAPI
    if SCRAPER_API_KEY:
        try:
            r = _requests.get(_sapi_url(url, params), headers=headers, timeout=60)
            if r.status_code == 200:
                logger.debug(f"[sapi:GET] OK {url}")
                return r
            logger.debug(f"[sapi:GET] status={r.status_code}")
        except Exception as e:
            logger.debug(f"[sapi:GET] excecao: {e}")

    # 3. requests puro (funciona para Carrefour e lojas sem CF)
    return _requests.get(url, headers=headers, params=params, timeout=timeout)


def post(url, *, json=None, headers=None, params=None, timeout=20):
    """POST: cloudscraper → ScraperAPI → requests puro."""
    cs = _get_scraper()
    if cs:
        try:
            r = cs.post(url, json=json, headers=headers, params=params, timeout=timeout)
            if r.status_code == 200 and _looks_like_json(r):
                return r
        except Exception as e:
            logger.debug(f"[cs:POST] excecao: {e}")

    if SCRAPER_API_KEY:
        try:
            r = _requests.post(_sapi_url(url, params), json=json, headers=headers, timeout=60)
            if r.status_code == 200:
                return r
        except Exception as e:
            logger.debug(f"[sapi:POST] excecao: {e}")

    return _requests.post(url, json=json, headers=headers, params=params, timeout=timeout)

"""Scraper Shoptime - grupo Americanas (VTEX IS)."""
from ._vtex_base import scrape_vtex_store

def get_prices() -> list:
    return scrape_vtex_store("https://www.shoptime.com.br", "shoptime", "Shoptime")

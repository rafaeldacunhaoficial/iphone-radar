"""Scraper Vivo Store - VTEX Intelligent Search."""
from ._vtex_base import scrape_vtex_store

def get_prices() -> list:
    return scrape_vtex_store("https://store.vivo.com.br", "vivo_store", "Vivo Store")

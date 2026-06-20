"""Scraper Casas Bahia (VTEX)."""
from ._vtex_base import scrape_vtex_store

def get_prices(): return scrape_vtex_store("https://www.casasbahia.com.br", "casasbahia", "Casas Bahia")

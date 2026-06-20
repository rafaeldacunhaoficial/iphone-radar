"""Scraper iPlace — Apple Premium Reseller (VTEX)."""
from ._vtex_base import scrape_vtex_store

def get_prices(): return scrape_vtex_store("https://www.iplace.com.br", "iplace", "iPlace")

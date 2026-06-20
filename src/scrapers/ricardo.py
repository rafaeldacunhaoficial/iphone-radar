"""Scraper Ricardo Eletro (VTEX)."""
from ._vtex_base import scrape_vtex_store

def get_prices(): return scrape_vtex_store("https://www.ricardoeletro.com.br", "ricardo", "Ricardo Eletro")

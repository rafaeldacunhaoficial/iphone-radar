"""Scraper Conecta (VTEX)."""
from ._vtex_base import scrape_vtex_store

def get_prices(): return scrape_vtex_store("https://www.conecta.com.br", "conecta", "Conecta")

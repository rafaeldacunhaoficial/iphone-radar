"""Scraper Ponto (ex-Pontofrio / Via Varejo) - VTEX Intelligent Search."""
from ._vtex_base import scrape_vtex_store

def get_prices() -> list:
    return scrape_vtex_store("https://www.pontofrio.com.br", "ponto", "Ponto")

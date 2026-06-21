"""Scraper Casas Bahia - VTEX Intelligent Search (via _vtex_base)."""
from ._vtex_base import scrape_vtex_store


def get_prices() -> list:
    return scrape_vtex_store(
        "https://www.casasbahia.com.br",
        "casasbahia",
        "Casas Bahia",
    )

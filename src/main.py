"""
iPhone Price Radar - orquestrador principal.

Fluxo:
  1. Carrega historico de precos (JSON)
  2. Coleta precos de todas as lojas configuradas
  3. Para cada oferta: atualiza historico, analisa e envia alerta se necessario
  4. Salva historico atualizado (sera commitado pelo GitHub Actions)
"""

import logging
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))

import price_db
import analyzer
import notifier
from scrapers import (
    mercadolivre,
    shopee,
    americanas,
    via_varejo,
    magalu,
    kabum,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SCRAPERS = [
    mercadolivre.get_prices,
    shopee.get_prices,
    americanas.get_prices,
    via_varejo.get_prices,
    magalu.get_prices,
    kabum.get_prices,
]


def main():
    logger.info("=== iPhone Price Radar iniciando ===")
    db = price_db.load()

    all_offers = []
    for scraper_fn in SCRAPERS:
        name = scraper_fn.__module__.split(".")[-1]
        try:
            offers = scraper_fn()
            logger.info(f"[{name}] {len(offers)} oferta(s) coletada(s)")
            all_offers.extend(offers)
        except Exception as e:
            logger.error(f"[{name}] Erro fatal: {e}")

    logger.info(f"Total de ofertas coletadas: {len(all_offers)}")

    alerts_sent = 0
    for offer in all_offers:
        pid = offer["product_id"]
        price = offer["price"]
        db = price_db.add_entry(db, pid, price)
        history = price_db.get_history(db, pid)
        alert = analyzer.analyze(offer, history)
        if alert:
            notifier.send(alert)
            alerts_sent += 1

    logger.info(f"Alertas enviados: {alerts_sent}")
    price_db.save(db)
    logger.info("=== Radar finalizado ===")


if __name__ == "__main__":
    main()

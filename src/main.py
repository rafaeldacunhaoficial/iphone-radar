"""iPhone Price Radar - orquestrador principal."""
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import price_db
import analyzer
import notifier
from scrapers import (
    carrefour,
    fastshop,
    iplace,
    extra,
    fnac,
    via_varejo,
    apple_store,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

SCRAPERS = [
    carrefour.get_prices,
    fastshop.get_prices,
    iplace.get_prices,
    extra.get_prices,
    fnac.get_prices,
    via_varejo.get_prices,
    apple_store.get_prices,
]


def main():
    logger.info("=== iPhone Price Radar iniciando ===")
    db = price_db.load_db()

    all_offers = []
    for scraper_fn in SCRAPERS:
        name = scraper_fn.__module__.split(".")[-1]
        try:
            offers = scraper_fn()
            logger.info(f"[{name}] {len(offers)} oferta(s)")
            all_offers.extend(offers)
        except Exception as e:
            logger.error(f"[{name}] Erro fatal: {e}")

    logger.info(f"Total coletado: {len(all_offers)}")

    alerts_sent = 0
    for offer in all_offers:
        try:
            price_db.update_price(db, offer)
            key = price_db._make_key(offer)
            record = db.get(key, {})
            stats = price_db.get_stats(record)
            alert = analyzer.analyze(offer["price"], stats)
            if analyzer.should_alert(alert) and not price_db.was_recently_alerted(record, offer["price"]):
                if notifier.send_alert(offer, alert):
                    price_db.mark_alerted(db, key, offer["price"])
                    alerts_sent += 1
        except Exception as e:
            logger.warning(f"Erro ao processar {offer.get('product_id')}: {e}")

    logger.info(f"Alertas enviados: {alerts_sent}")
    price_db.save_db(db)
    logger.info("=== Radar finalizado ===")


if __name__ == "__main__":
    main()

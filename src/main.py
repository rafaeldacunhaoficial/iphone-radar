"""iPhone Price Radar - orquestrador principal."""
import json
import concurrent.futures
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
import price_db
import analyzer
import notifier
from scrapers import (
    carrefour, iplace, fastshop, kabum,
    apple_store, casasbahia, mercadolivre, amazon,
    magalu, goimports, extra,
    via_varejo, americanas, shopee,
    submarino, shoptime, vivo_store,
    claro,
    bemol,
    terabyte,
    pmgimports,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

SCRAPERS = [
    carrefour.get_prices,
    iplace.get_prices,
    fastshop.get_prices,
    kabum.get_prices,
    apple_store.get_prices,
    casasbahia.get_prices,
    mercadolivre.get_prices,
    amazon.get_prices,
    magalu.get_prices,
    goimports.get_prices,
    extra.get_prices,
    via_varejo.get_prices,
    americanas.get_prices,
    shopee.get_prices,
    submarino.get_prices,
    shoptime.get_prices,
    vivo_store.get_prices,
    claro.get_prices,
    bemol.get_prices,
    terabyte.get_prices,
    pmgimports.get_prices,
]

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _write_debug(debug_info: dict) -> None:
    path = os.path.join(DATA_DIR, "debug.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(debug_info, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Nao foi possivel salvar debug.json: {e}")


def main() -> None:
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    logger.info(f"=== iPhone Price Radar iniciado em {run_ts} ===")

    db = price_db.load_db()
    all_offers = []
    debug_scrapers = {}

    for scraper_fn in SCRAPERS:
        name = scraper_fn.__module__.split(".")[-1]
        try:
            _ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            _fut = _ex.submit(scraper_fn)
            try:
                offers = _fut.result(timeout=30)
            except concurrent.futures.TimeoutError:
                logger.warning(f"[{name}] TIMEOUT apos 30s ÃÂ¢ÃÂÃÂ pulando")
                offers = []
            finally:
                _ex.shutdown(wait=False)
            count = len(offers)
            logger.info(f"[{name}] {count} oferta(s)")
            all_offers.extend(offers)
            extra = getattr(scraper_fn, "_last_debug", None)
            debug_scrapers[name] = {"count": count, "error": None, "detail": extra}
        except Exception as e:
            logger.error(f"[{name}] Erro fatal: {e}", exc_info=True)
            debug_scrapers[name] = {"count": 0, "error": str(e), "detail": None}

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

    price_db.save_db(db)
    debug_info = {
        "run_time": run_ts,
        "total_offers": len(all_offers),
        "alerts_sent": alerts_sent,
        "scrapers": debug_scrapers,
    }
    _write_debug(debug_info)
    logger.info(f"=== Concluido: {len(all_offers)} ofertas, {alerts_sent} alertas enviados ===")


if __name__ == "__main__":
    main()

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
    carrefour,
    iplace,
    kabum,
    apple_store,
    amazon,
    goimports,
    bemol,
    pmgimports,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Lojas ativas (funcionam de GitHub Actions)
# carrefour  – VTEX sem CF bot fight
# iplace     – VTEX sem CF bot fight
# kabum      – API própria
# apple_store– API Apple
# amazon     – HTML scraping (pode cair temporariamente)
# goimports  – OpenCart SSR
# bemol      – VTEX vtexcommercestable
# pmgimports – NuvemShop SSR
SCRAPERS = [
    carrefour.get_prices,
    iplace.get_prices,
    kabum.get_prices,
    apple_store.get_prices,
    amazon.get_prices,
    goimports.get_prices,
    bemol.get_prices,
    pmgimports.get_prices,
]


def _run_scraper(fn):
    name = fn.__module__.split(".")[-1]
    try:
        items = fn()
        count = len(items) if items else 0
        detail = getattr(fn, "_last_debug", None)
        return name, items or [], count, None, detail
    except Exception as exc:
        logger.error(f"[{name}] ERRO: {exc}", exc_info=True)
        return name, [], 0, str(exc), None


def main():
    logger.info("=== iPhone Price Radar iniciado ===")
    start = datetime.now(timezone.utc)

    all_items = []
    debug_scrapers = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_run_scraper, fn): fn for fn in SCRAPERS}
        for fut in concurrent.futures.as_completed(futures):
            name, items, count, error, detail = fut.result()
            all_items.extend(items)
            debug_scrapers[name] = {"count": count, "error": error, "detail": detail}
            logger.info(f"[{name}] {count} iPhones")

    logger.info(f"Total bruto: {len(all_items)} itens")

    # Salva no histórico e analisa
    price_db.save(all_items)
    alerts = analyzer.analyze(all_items)
    if alerts:
        notifier.send(alerts)
        logger.info(f"{len(alerts)} alertas enviados.")
    else:
        logger.info("Sem alertas.")

    # Salva debug
    debug = {
        "run_at": start.isoformat(),
        "total_items": len(all_items),
        "alerts": len(alerts),
        "scrapers": debug_scrapers,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/debug.json", "w", encoding="utf-8") as f:
        json.dump(debug, f, ensure_ascii=False, indent=2)

    logger.info("=== Concluído ===")


if __name__ == "__main__":
    main()

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


def run_scraper(fn):
    name = fn.__module__.split(".")[-1]
    try:
        items = fn() or []
        clean = []
        for item in items:
            item.setdefault("title", item.get("model", ""))
            item.setdefault("url", "")
            item.setdefault("seller", item.get("store", ""))
            item.setdefault(
                "product_id",
                str(abs(hash(item.get("model", ""))) % 9999999),
            )
            clean.append(item)
        detail = getattr(fn, "_last_debug", None)
        return name, clean, len(clean), None, detail
    except Exception as e:
        logger.error(f"[{name}] Erro: {e}")
        detail = getattr(fn, "_last_debug", None)
        return name, [], 0, str(e), detail


def main():
    start = datetime.now(tz=timezone.utc)
    logger.info("=== iPhone Price Radar iniciado ===")

    all_items = []
    debug_scrapers = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(run_scraper, fn): fn for fn in SCRAPERS}
        for fut in concurrent.futures.as_completed(futures):
            name, items, count, error, detail = fut.result()
            all_items.extend(items)
            debug_scrapers[name] = {"count": count, "error": error, "detail": detail}
            logger.info(f"[{name}] {count} iPhones")

    logger.info(f"Total bruto: {len(all_items)} itens")

    # Atualiza historico
    db = price_db.load_db()
    for item in all_items:
        try:
            price_db.update_price(db, item)
        except Exception as e:
            logger.warning(f"update_price {item.get('store')}/{item.get('product_id')}: {e}")
    price_db.save_db(db)

    # Analisa e notifica por item
    alerts_sent = 0
    for item in all_items:
        try:
            key = f"{item['store']}_{item['product_id']}"
            record = db.get(key, {})
            stats = price_db.get_stats(record)
            alert = analyzer.analyze(item["price"], stats)
            if analyzer.should_alert(alert) and not price_db.was_recently_alerted(record, item["price"]):
                if notifier.send_alert(item, alert):
                    price_db.mark_alerted(db, key, item["price"])
                    alerts_sent += 1
        except Exception as e:
            logger.warning(f"analyze/notify {item.get('store')}: {e}")

    if alerts_sent:
        price_db.save_db(db)
        logger.info(f"{alerts_sent} alertas enviados.")
    else:
        logger.info("Sem alertas.")

    # Salva debug
    debug = {
        "run_at": start.isoformat(),
        "total_items": len(all_items),
        "alerts": alerts_sent,
        "scrapers": debug_scrapers,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/debug.json", "w", encoding="utf-8") as f:
        json.dump(debug, f, ensure_ascii=False, indent=2)

    logger.info("=== Concluido ===")


if __name__ == "__main__":
    main()

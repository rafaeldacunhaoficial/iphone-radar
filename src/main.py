"""
iPhone Price Radar — orquestrador principal.

Fluxo:
  1. Carrega histórico de preços (JSON)
  2. Coleta preços de todas as lojas configuradas
  3. Para cada oferta: atualiza histórico, analisa e envia alerta se necessário
  4. Salva histórico atualizado (será commitado pelo GitHub Actions)
"""

import logging
import sys
import os
from datetime import datetime, timezone

# Adiciona /src ao path para imports relativos
sys.path.insert(0, os.path.dirname(__file__))

import price_db
import analyzer
import notifier
from scrapers import (
    mercadolivre, amazon, magalu, kabum,
    americanas, via_varejo, shopee, fastshop, iplace,
    extra, carrefour, fnac, terabyte, apple_store,
    zoom, ricardo, conecta,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 20 lojas monitoradas — comente qualquer linha para desativar temporariamente
SCRAPERS = [
    # ── Lojas grandes ──────────────────────────────────────
    ("MercadoLivre",   mercadolivre.get_prices),
    ("Amazon BR",      amazon.get_prices),
    ("Magazine Luiza", magalu.get_prices),
    ("KaBuM!",         kabum.get_prices),
    ("Americanas",     americanas.get_prices),   # inclui Submarino + Shoptime
    ("Casas Bahia",    via_varejo.get_prices),   # inclui Ponto
    ("Shopee BR",      shopee.get_prices),
    ("FastShop",       fastshop.get_prices),
    ("iPlace",         iplace.get_prices),
    # ── Lojas menores ──────────────────────────────────────
    ("Extra",          extra.get_prices),
    ("Carrefour",      carrefour.get_prices),
    ("Fnac",           fnac.get_prices),
    ("Terabyte Shop",  terabyte.get_prices),
    ("Apple Store",    apple_store.get_prices),
    ("Zoom",           zoom.get_prices),
    ("Ricardo Eletro", ricardo.get_prices),
    ("Conecta",        conecta.get_prices),
]


def run():
    logger.info("=" * 60)
    logger.info("🚀 iPhone Radar iniciado")
    logger.info(f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"🏪 {len(SCRAPERS)} lojas monitoradas")
    logger.info("=" * 60)

    # Carrega banco de dados
    db = price_db.load_db()

    all_items = []
    alerts_sent = 0

    # Coleta preços de todas as lojas
    for store_name, scraper_fn in SCRAPERS:
        logger.info(f"🔍 Coletando: {store_name}...")
        try:
            items = scraper_fn()
            all_items.extend(items)
            logger.info(f"   ✓ {len(items)} itens")
        except Exception as e:
            logger.error(f"   ✗ Erro em {store_name}: {e}")

    logger.info(f"\n📦 Total de ofertas coletadas: {len(all_items)}")

    # Processa cada oferta
    for item in all_items:
        try:
            key = f"{item['store']}_{item['model']}_{item['product_id']}"

            # Atualiza histórico
            price_db.update_price(db, item)
            record = db.get(key, {})

            # Calcula estatísticas
            stats = price_db.get_stats(record)

            # Analisa preço
            alert = analyzer.analyze(item["price"], stats)

            # Verifica se deve enviar alerta
            if not analyzer.should_alert(alert):
                continue

            # Evita spam (mesmo preço nas últimas 24h)
            if price_db.was_recently_alerted(record, item["price"]):
                logger.debug(f"Alerta recente ignorado: {item['title'][:50]}")
                continue

            # Envia alerta
            logger.info(
                f"🔔 {alert.level.value}: {item['model']} "
                f"R${item['price']:.2f} em {item['store']}"
            )
            sent = notifier.send_alert(item, alert)

            if sent:
                price_db.mark_alerted(db, key, item["price"])
                alerts_sent += 1

        except Exception as e:
            logger.error(f"Erro ao processar {item.get('title', '?')[:50]}: {e}")

    # Salva banco atualizado
    price_db.save_db(db)
    logger.info(
        f"\n\u2705 Concluído — {alerts_sent} alertas enviados, "
        f"{len(db)} produtos rastreados."
    )

    # Heartbeat diário (às 09:00 UTC)
    if datetime.now(timezone.utc).hour == 9:
        _send_daily_summary(db)


def _send_daily_summary(db: dict):
    total = len(db)
    by_store: dict[str, int] = {}
    for record in db.values():
        store = record.get("store", "?")
        by_store[store] = by_store.get(store, 0) + 1

    lines = [f"🛒 Produtos monitorados: {total}"]
    for store, count in sorted(by_store.items()):
        lines.append(f"  • {store}: {count}")

    notifier.send_heartbeat("\n".join(lines))


if __name__ == "__main__":
    run()

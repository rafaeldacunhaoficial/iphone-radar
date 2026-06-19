"""
Banco de dados de preços — arquivo JSON no repositório.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent.parent / "data" / "prices.json"

MAX_AGE_DAYS = 180
ALERT_COOLDOWN_HOURS = 24
ALERT_PRICE_BAND = 0.02


def load_db() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Erro ao carregar DB: {e}")
    return {}


def save_db(db: dict) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_key(item: dict) -> str:
    return f"{item['store']}_{item['model']}_{item['product_id']}"


def update_price(db: dict, item: dict) -> None:
    key = _make_key(item)
    now = datetime.now(tz=timezone.utc)

    if key not in db:
        db[key] = {
            "store": item["store"],
            "model": item["model"],
            "title": item["title"],
            "samples": [],
            "last_alerted_price": None,
            "last_alerted_at": None,
        }

    record = db[key]
    record["title"] = item["title"]
    record["samples"].append({
        "timestamp": now.isoformat(),
        "price": item["price"],
        "url": item.get("url", ""),
    })

    cutoff = now.timestamp() - MAX_AGE_DAYS * 86400
    record["samples"] = [
        s for s in record["samples"]
        if datetime.fromisoformat(s["timestamp"]).replace(tzinfo=timezone.utc).timestamp() > cutoff
    ]


def get_stats(record: dict) -> dict:
    samples = record.get("samples", [])
    if not samples:
        return {"min_6m": None, "avg_6m": None, "count": 0}
    prices = [float(s["price"]) for s in samples]
    return {
        "min_6m": min(prices),
        "avg_6m": sum(prices) / len(prices),
        "count": len(prices),
    }


def was_recently_alerted(record: dict, price: float) -> bool:
    last_price = record.get("last_alerted_price")
    last_at = record.get("last_alerted_at")
    if not last_price or not last_at:
        return False
    now = datetime.now(tz=timezone.utc)
    last_dt = datetime.fromisoformat(last_at).replace(tzinfo=timezone.utc)
    hours_since = (now - last_dt).total_seconds() / 3600
    if hours_since < ALERT_COOLDOWN_HOURS:
        price_drop_pct = (last_price - price) / last_price
        if price_drop_pct < ALERT_PRICE_BAND:
            return True
    return False


def mark_alerted(db: dict, key: str, price: float) -> None:
    if key in db:
        db[key]["last_alerted_price"] = price
        db[key]["last_alerted_at"] = datetime.now(tz=timezone.utc).isoformat()

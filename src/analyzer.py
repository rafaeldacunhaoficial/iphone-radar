"""
Engine de análise de preços.

Classifica cada oferta em:
  - BUG       🚨  Preço > 25% abaixo da média de 6 meses (provável erro de precificação)
  - MINIMO    ⭐  Menor preço visto nos últimos 6 meses (novo mínimo histórico)
  - OFERTA    🔥  Preço abaixo da média dos últimos 6 meses (boa oportunidade)
  - NORMAL    —   Preço dentro da faixa normal (sem alerta)

Regras:
  - BUG exige pelo menos 7 amostras (para ter contexto histórico mínimo)
  - MINIMO exige pelo menos 3 amostras
  - Sem histórico suficiente: classifica como OFERTA se for um preço razoável
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AlertLevel(str, Enum):
    BUG = "BUG"
    MINIMO = "MINIMO"
    OFERTA = "OFERTA"
    NORMAL = "NORMAL"


@dataclass
class PriceAlert:
    level: AlertLevel
    current_price: float
    min_6m: Optional[float]
    avg_6m: Optional[float]
    pct_vs_avg: Optional[float]   # % abaixo da média (positivo = abaixo)
    pct_vs_min: Optional[float]   # % vs mínimo histórico
    sample_count: int
    is_new_minimum: bool


# Thresholds
BUG_THRESHOLD_PCT = 0.25       # 25% abaixo da média = bug
OFFER_THRESHOLD_PCT = 0.05     # 5% abaixo da média = oferta
MIN_SAMPLES_FOR_BUG = 7
MIN_SAMPLES_FOR_MINIMUM = 3


def analyze(current_price: float, stats: dict) -> PriceAlert:
    """
    Analisa o preço atual com base nas estatísticas históricas.

    Args:
        current_price: Preço atual da oferta.
        stats: Dict com min_6m, avg_6m, sample_count (de price_db.get_stats).

    Returns:
        PriceAlert com o nível de alerta e contexto.
    """
    min_6m = stats.get("min_6m")
    avg_6m = stats.get("avg_6m")
    sample_count = stats.get("sample_count", 0)

    # Sem histórico suficiente
    if min_6m is None or avg_6m is None or sample_count < 1:
        return PriceAlert(
            level=AlertLevel.NORMAL,
            current_price=current_price,
            min_6m=None,
            avg_6m=None,
            pct_vs_avg=None,
            pct_vs_min=None,
            sample_count=0,
            is_new_minimum=False,
        )

    pct_vs_avg = (avg_6m - current_price) / avg_6m  # positivo = abaixo da média
    pct_vs_min = (current_price - min_6m) / min_6m  # negativo = novo mínimo

    is_new_minimum = (current_price < min_6m) and (sample_count >= MIN_SAMPLES_FOR_MINIMUM)

    # Determina nível
    if sample_count >= MIN_SAMPLES_FOR_BUG and pct_vs_avg >= BUG_THRESHOLD_PCT:
        level = AlertLevel.BUG
    elif is_new_minimum:
        level = AlertLevel.MINIMO
    elif pct_vs_avg >= OFFER_THRESHOLD_PCT:
        level = AlertLevel.OFERTA
    else:
        level = AlertLevel.NORMAL

    return PriceAlert(
        level=level,
        current_price=current_price,
        min_6m=min_6m,
        avg_6m=avg_6m,
        pct_vs_avg=round(pct_vs_avg * 100, 1),
        pct_vs_min=round(pct_vs_min * 100, 1),
        sample_count=sample_count,
        is_new_minimum=is_new_minimum,
    )


def should_alert(alert: PriceAlert) -> bool:
    """Retorna True se o alerta merece ser enviado ao Telegram."""
    return alert.level in (AlertLevel.BUG, AlertLevel.MINIMO, AlertLevel.OFERTA)

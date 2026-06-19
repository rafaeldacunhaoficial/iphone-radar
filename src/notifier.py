"""
Notificador Telegram.
Envia alertas formatados para o grupo configurado via variáveis de ambiente.

Variáveis necessárias:
  TELEGRAM_BOT_TOKEN  — token do bot (BotFather)
  TELEGRAM_CHAT_ID    — ID do grupo (ex: -1001234567890)
"""

import logging
import os
import requests
from analyzer import AlertLevel, PriceAlert

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

STORE_NAMES = {
    "mercadolivre": "Mercado Livre",
    "amazon": "Amazon BR",
    "magalu": "Magazine Luiza",
    "kabum": "KaBuM!",
    "americanas": "Americanas",
    "submarino": "Submarino",
    "shoptime": "Shoptime",
    "casasbahia": "Casas Bahia",
    "ponto": "Ponto",
    "shopee": "Shopee BR",
    "fastshop": "FastShop",
    "iplace": "iPlace",
    "extra": "Extra",
    "carrefour": "Carrefour",
    "fnac": "Fnac",
    "terabyte": "Terabyte Shop",
    "apple_store": "Apple Store",
    "zoom": "Zoom",
    "ricardo": "Ricardo Eletro",
    "conecta": "Conecta",
}

LEVEL_HEADERS = {
    AlertLevel.BUG: "🚨 *BUG DE PREÇO DETECTADO!*",
    AlertLevel.MINIMO: "⭐ *MENOR PREÇO EM 6 MESES!*",
    AlertLevel.OFERTA: "🔥 *BOA OFERTA ENCONTRADA!*",
}


def _format_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _build_message(item: dict, alert: PriceAlert) -> str:
    store_name = STORE_NAMES.get(item["store"], item["store"].title())
    header = LEVEL_HEADERS.get(alert.level, "💡 Alerta de Preço")

    lines = [
        header,
        "",
        f"📱 *{item['model']}*",
        f"🏪 Loja: {store_name}",
        f"🏷️ {item['title'][:80]}{'...' if len(item['title']) > 80 else ''}",
        f"💰 Preço: *{_format_brl(alert.current_price)}*",
    ]

    # Contexto histórico
    if alert.avg_6m and alert.sample_count >= 3:
        lines.append(f"📊 Média 6 meses: {_format_brl(alert.avg_6m)}")
        if alert.pct_vs_avg and alert.pct_vs_avg > 0:
            lines.append(f"📉 {alert.pct_vs_avg:.1f}% abaixo da média")

    if alert.min_6m and alert.sample_count >= 3:
        if alert.is_new_minimum:
            lines.append(f"🏆 Novo mínimo histórico! (anterior: {_format_brl(alert.min_6m)})")
        else:
            lines.append(f"🔻 Mínimo 6 meses: {_format_brl(alert.min_6m)}")

    if alert.level == AlertLevel.BUG:
        lines.append("")
        lines.append("⚠️ _Compre rápido — bugs de preço costumam ser corrigidos em minutos!_")

    lines.append("")
    lines.append(f"🔗 [Ver produto]({item['url']})")

    return "\n".join(lines)


def send_alert(item: dict, alert: PriceAlert) -> bool:
    """
    Envia mensagem para o grupo Telegram.
    Retorna True se enviou com sucesso.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        logger.error("TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID não configurados.")
        return False

    message = _build_message(item, alert)

    try:
        resp = requests.post(
            TELEGRAM_API.format(token=token),
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            logger.info(f"✅ Alerta enviado: {item['model']} - {_format_brl(alert.current_price)}")
            return True
        else:
            logger.warning(f"Telegram retornou {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Erro ao enviar alerta: {e}")
        return False


def send_heartbeat(stats_summary: str) -> None:
    """Envia resumo periódico (a cada 24h) ao grupo."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat_id:
        return

    try:
        requests.post(
            TELEGRAM_API.format(token=token),
            json={
                "chat_id": chat_id,
                "text": f"📡 *iPhone Radar — Resumo diário*\n\n{stats_summary}",
                "parse_mode": "Markdown",
            },
            timeout=15,
        )
    except Exception as e:
        logger.warning(f"Heartbeat falhou: {e}")

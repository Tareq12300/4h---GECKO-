from __future__ import annotations

import html
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

from config import Settings
from models import CmcAsset, MarketLocation, StochRsiSnapshot


logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.api_url = (
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        )
        self.timezone = ZoneInfo(settings.timezone)

    def send(self, text: str) -> bool:
        if not self.settings.enable_telegram_alerts:
            logger.info("Telegram معطل. الرسالة:\n%s", text)
            return True

        try:
            response = self.session.post(
                self.api_url,
                json={
                    "chat_id": self.settings.telegram_chat_id,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=self.settings.telegram_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("ok"):
                raise RuntimeError(payload.get("description", "Telegram API error"))
            return True
        except Exception as exc:
            logger.error("فشل إرسال رسالة Telegram: %s", exc)
            return False

    def send_startup(self) -> bool:
        text = (
            "🤖 <b>بوت Stoch RSI + CMC يعمل الآن</b>\n\n"
            f"⏱ الفريم: <b>{html.escape(self.settings.timeframe)}</b>\n"
            f"📊 نطاق K: <b>{self.settings.min_stoch_k:g} - {self.settings.max_stoch_k:g}</b>\n"
            f"📊 نطاق D: <b>{self.settings.min_stoch_d:g} - {self.settings.max_stoch_d:g}</b>\n"
            f"💵 أقل فوليوم CMC: <b>{format_money(self.settings.min_cmc_volume_24h)}</b>\n"
            f"🪙 أقصى عدد عملات: <b>{self.settings.max_coins}</b>\n"
            f"🏦 المنصات: <b>{html.escape(', '.join(self.settings.exchanges))}</b>\n"
            f"🔁 الفحص كل: <b>{self.settings.check_interval_seconds} ثانية</b>"
        )
        return self.send(text)

    def send_signal(
        self,
        asset: CmcAsset,
        location: MarketLocation,
        stoch: StochRsiSnapshot,
    ) -> bool:
        now = datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            "🚨 <b>إشارة شراء جديدة</b>",
            "",
            f"🪙 العملة: <b>{html.escape(asset.symbol)}/{html.escape(self.settings.quote_currency)}</b>",
            f"📛 الاسم: <b>{html.escape(asset.name)}</b>",
            f"🏦 المنصة: <b>{html.escape(location.exchange_name)}</b>",
            f"⏱ الفريم: <b>{html.escape(self.settings.timeframe)}</b>",
        ]

        if self.settings.show_stoch_values:
            lines.extend(
                [
                    "",
                    "📊 <b>Stoch RSI</b>",
                    f"K السابق: <b>{stoch.previous_k:.2f}</b>",
                    f"D السابق: <b>{stoch.previous_d:.2f}</b>",
                    f"K الحالي: <b>{stoch.current_k:.2f}</b>",
                    f"D الحالي: <b>{stoch.current_d:.2f}</b>",
                ]
            )

        if self.settings.show_cmc_volume:
            lines.extend(
                [
                    "",
                    f"💰 فوليوم CoinMarketCap 24H: <b>{format_money(asset.volume_24h_usd)}</b>",
                ]
            )

        lines.extend(["", f"🕒 الوقت: <b>{now}</b>"])

        if self.settings.show_tradingview_link:
            tv_symbol = tradingview_symbol(location.exchange_id, asset.symbol, self.settings.quote_currency)
            lines.extend(
                [
                    "",
                    f'🔗 <a href="https://www.tradingview.com/chart/?symbol={tv_symbol}">فتح TradingView</a>',
                ]
            )

        return self.send("\n".join(lines))

    def send_summary(
        self,
        checked: int,
        pairs_found: int,
        signals: int,
        errors: int,
        duration_seconds: float,
    ) -> bool:
        return self.send(
            "📋 <b>ملخص الفحص</b>\n\n"
            f"🪙 العملات المفحوصة: <b>{checked}</b>\n"
            f"🔗 الأزواج المتاحة: <b>{pairs_found}</b>\n"
            f"🚨 الإشارات: <b>{signals}</b>\n"
            f"⚠️ الأخطاء: <b>{errors}</b>\n"
            f"⏳ المدة: <b>{duration_seconds:.1f} ثانية</b>"
        )


def format_money(value: float) -> str:
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:.2f}K"
    return f"${value:.2f}"


def tradingview_symbol(exchange_id: str, base: str, quote: str) -> str:
    prefixes = {
        "gateio": "GATEIO",
        "kucoin": "KUCOIN",
        "mexc": "MEXC",
    }
    prefix = prefixes.get(exchange_id.lower(), exchange_id.upper())
    pair = "".join(character for character in f"{base}{quote}" if character.isalnum())
    return f"{prefix}:{pair}"

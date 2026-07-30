from __future__ import annotations

import logging
import time
from typing import Any

import ccxt

from config import Settings
from models import MarketLocation


logger = logging.getLogger(__name__)


class ExchangeManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.exchanges: dict[str, Any] = {}
        self.market_cache: dict[str, MarketLocation | None] = {}

    def initialize(self) -> None:
        for exchange_id in self.settings.exchanges:
            exchange_class = getattr(ccxt, exchange_id, None)
            if exchange_class is None:
                logger.error("المنصة غير مدعومة في CCXT: %s", exchange_id)
                continue

            try:
                exchange = exchange_class(
                    {
                        "enableRateLimit": True,
                        "timeout": self.settings.exchange_timeout_ms,
                        "options": {"defaultType": "spot"},
                    }
                )
                exchange.load_markets()
                if not exchange.has.get("fetchOHLCV"):
                    logger.warning("المنصة %s لا تدعم fetchOHLCV", exchange_id)
                    continue
                self.exchanges[exchange_id] = exchange
                logger.info(
                    "تم تحميل %s: عدد الأسواق %s",
                    exchange_id,
                    len(exchange.markets),
                )
            except Exception as exc:  # أخطاء المنصات تختلف حسب CCXT
                logger.exception("تعذر تحميل المنصة %s: %s", exchange_id, exc)

        if not self.exchanges:
            raise RuntimeError("لم يتم تحميل أي منصة بنجاح")

    def resolve_market(self, base: str) -> MarketLocation | None:
        base = base.upper()
        cached = self.market_cache.get(base)
        if base in self.market_cache:
            return cached

        unified_symbol = f"{base}/{self.settings.quote_currency}"

        for exchange_id in self.settings.exchanges:
            exchange = self.exchanges.get(exchange_id)
            if exchange is None:
                continue

            market = exchange.markets.get(unified_symbol)
            if not market:
                continue
            if market.get("spot") is False:
                continue
            if market.get("active") is False:
                continue

            location = MarketLocation(
                exchange_id=exchange_id,
                exchange_name=str(exchange.name),
                symbol=unified_symbol,
            )
            self.market_cache[base] = location
            return location

        self.market_cache[base] = None
        return None

    def fetch_closes(self, location: MarketLocation) -> list[float] | None:
        exchange = self.exchanges[location.exchange_id]

        for attempt in range(1, self.settings.exchange_retries + 2):
            try:
                candles = exchange.fetch_ohlcv(
                    location.symbol,
                    timeframe=self.settings.timeframe,
                    limit=self.settings.candle_limit,
                )

                if self.settings.use_closed_candle and len(candles) > 1:
                    candles = candles[:-1]

                closes = [float(candle[4]) for candle in candles if len(candle) >= 5]
                return closes if closes else None
            except (
                ccxt.NetworkError,
                ccxt.ExchangeNotAvailable,
                ccxt.RequestTimeout,
                ccxt.DDoSProtection,
            ) as exc:
                logger.warning(
                    "خطأ مؤقت %s %s، المحاولة %s: %s",
                    location.exchange_id,
                    location.symbol,
                    attempt,
                    exc,
                )
                if attempt <= self.settings.exchange_retries:
                    time.sleep(min(2**attempt, 8))
            except (ccxt.BadSymbol, ccxt.NotSupported) as exc:
                logger.debug("السوق غير متاح %s: %s", location.symbol, exc)
                return None
            except Exception as exc:
                logger.warning(
                    "تعذر جلب شموع %s من %s: %s",
                    location.symbol,
                    location.exchange_id,
                    exc,
                )
                return None

        return None

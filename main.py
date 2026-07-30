from __future__ import annotations

import logging
import signal
import sys
import time
from dataclasses import dataclass

from cmc_client import CoinMarketCapClient
from config import Settings
from exchange_manager import ExchangeManager
from indicators import calculate_stoch_rsi
from signal_rules import is_buy_signal
from state_store import AlertStateStore
from telegram_client import TelegramClient


logger = logging.getLogger(__name__)
STOP_REQUESTED = False


@dataclass
class ScanStats:
    checked: int = 0
    pairs_found: int = 0
    signals: int = 0
    errors: int = 0


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def request_stop(signum: int, _frame: object) -> None:
    global STOP_REQUESTED
    STOP_REQUESTED = True
    logger.info("تم استلام إشارة الإيقاف %s", signum)


def signal_key(exchange_id: str, symbol: str, timeframe: str) -> str:
    return f"{exchange_id}:{symbol}:{timeframe}"


def run_scan(
    settings: Settings,
    cmc: CoinMarketCapClient,
    exchanges: ExchangeManager,
    telegram: TelegramClient,
    state: AlertStateStore,
) -> ScanStats:
    stats = ScanStats()
    assets = cmc.fetch_assets()
    logger.info("تم جلب %s عملة مؤهلة من CoinMarketCap", len(assets))

    for asset in assets:
        if STOP_REQUESTED:
            break

        stats.checked += 1
        try:
            location = exchanges.resolve_market(asset.symbol)
            if location is None:
                logger.debug("لا يوجد زوج %s/USDT في المنصات المحددة", asset.symbol)
                continue

            stats.pairs_found += 1
            closes = exchanges.fetch_closes(location)
            if not closes:
                stats.errors += 1
                continue

            stoch = calculate_stoch_rsi(
                closes=closes,
                rsi_period=settings.rsi_period,
                stoch_period=settings.stoch_period,
                k_smoothing=settings.k_smoothing,
                d_smoothing=settings.d_smoothing,
            )
            if stoch is None:
                logger.debug("شموع غير كافية لحساب %s", location.symbol)
                continue

            if not is_buy_signal(asset, stoch, settings):
                continue

            key = signal_key(location.exchange_id, location.symbol, settings.timeframe)
            if not state.can_send(key, settings.cooldown_hours):
                logger.info("إشارة %s ضمن فترة التهدئة", location.symbol)
                continue

            if telegram.send_signal(asset, location, stoch):
                state.mark_sent(key)
                stats.signals += 1
                logger.info(
                    "تم إرسال إشارة %s | K %.2f | D %.2f | CMC volume %.2f",
                    location.symbol,
                    stoch.current_k,
                    stoch.current_d,
                    asset.volume_24h_usd,
                )
        except Exception as exc:
            stats.errors += 1
            logger.exception("خطأ أثناء فحص %s: %s", asset.symbol, exc)

        if settings.scan_delay_seconds > 0:
            time.sleep(settings.scan_delay_seconds)

    return stats


def sleep_interruptibly(seconds: int) -> None:
    end_time = time.monotonic() + seconds
    while not STOP_REQUESTED and time.monotonic() < end_time:
        time.sleep(min(1.0, end_time - time.monotonic()))


def main() -> int:
    try:
        settings = Settings.from_env()
    except Exception as exc:
        print(f"خطأ في الإعدادات: {exc}", file=sys.stderr)
        return 1

    configure_logging(settings.log_level)
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    logger.info("تشغيل بوت Stoch RSI + CoinMarketCap Volume")
    cmc = CoinMarketCapClient(settings)
    exchanges = ExchangeManager(settings)
    telegram = TelegramClient(settings)
    state = AlertStateStore(settings.state_file)

    try:
        exchanges.initialize()
    except Exception as exc:
        logger.exception("تعذر بدء المنصات: %s", exc)
        return 1

    if settings.send_startup_message:
        telegram.send_startup()

    while not STOP_REQUESTED:
        started = time.monotonic()
        try:
            stats = run_scan(settings, cmc, exchanges, telegram, state)
        except Exception as exc:
            logger.exception("فشل دورة الفحص: %s", exc)
            stats = ScanStats(errors=1)

        duration = time.monotonic() - started
        logger.info(
            "انتهى الفحص | checked=%s pairs=%s signals=%s errors=%s duration=%.1fs",
            stats.checked,
            stats.pairs_found,
            stats.signals,
            stats.errors,
            duration,
        )

        if settings.send_scan_summary:
            telegram.send_summary(
                checked=stats.checked,
                pairs_found=stats.pairs_found,
                signals=stats.signals,
                errors=stats.errors,
                duration_seconds=duration,
            )

        if not STOP_REQUESTED:
            sleep_interruptibly(settings.check_interval_seconds)

    logger.info("تم إيقاف البوت بأمان")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

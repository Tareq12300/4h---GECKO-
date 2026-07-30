from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def env_str(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"المتغير {name} يجب أن يكون رقمًا صحيحًا، والقيمة الحالية: {raw!r}") from exc


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"المتغير {name} يجب أن يكون رقمًا، والقيمة الحالية: {raw!r}") from exc


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on", "enabled"}:
        return True
    if value in {"0", "false", "no", "off", "disabled"}:
        return False
    raise ValueError(
        f"المتغير {name} يجب أن يكون true أو false، والقيمة الحالية: {raw!r}"
    )


def env_list(name: str, default: str = "") -> tuple[str, ...]:
    raw = os.getenv(name, default)
    return tuple(item.strip().upper() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str
    enable_telegram_alerts: bool
    send_startup_message: bool
    send_scan_summary: bool
    telegram_timeout_seconds: int

    # CoinMarketCap
    cmc_api_key: str
    cmc_api_url: str
    cmc_convert: str
    cmc_limit: int
    cmc_timeout_seconds: int
    min_cmc_volume_24h: float
    max_cmc_volume_24h: float
    enable_max_cmc_volume: bool

    # Scanner
    timeframe: str
    check_interval_seconds: int
    scan_delay_seconds: float
    max_coins: int
    candle_limit: int
    cooldown_hours: float
    use_closed_candle: bool
    quote_currency: str
    exchanges: tuple[str, ...]
    excluded_coins: tuple[str, ...]
    excluded_stablecoins: tuple[str, ...]
    exchange_timeout_ms: int
    exchange_retries: int

    # Stoch RSI
    rsi_period: int
    stoch_period: int
    k_smoothing: int
    d_smoothing: int
    max_stoch_k: float
    max_stoch_d: float
    min_stoch_k: float
    min_stoch_d: float
    require_bullish_cross: bool
    require_k_rising: bool
    require_d_rising: bool

    # Display/logging/state
    timezone: str
    log_level: str
    state_file: Path
    show_tradingview_link: bool
    show_cmc_volume: bool
    show_stoch_values: bool

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            telegram_bot_token=env_str("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=env_str("TELEGRAM_CHAT_ID"),
            enable_telegram_alerts=env_bool("ENABLE_TELEGRAM_ALERTS", True),
            send_startup_message=env_bool("SEND_STARTUP_MESSAGE", True),
            send_scan_summary=env_bool("SEND_SCAN_SUMMARY", False),
            telegram_timeout_seconds=env_int("TELEGRAM_TIMEOUT_SECONDS", 20),
            cmc_api_key=env_str("CMC_API_KEY"),
            cmc_api_url=env_str(
                "CMC_API_URL",
                "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
            ),
            cmc_convert=env_str("CMC_CONVERT", "USD").upper(),
            cmc_limit=env_int("CMC_LIMIT", 1000),
            cmc_timeout_seconds=env_int("CMC_TIMEOUT_SECONDS", 30),
            min_cmc_volume_24h=env_float("MIN_CMC_VOLUME_24H", 3_000_000),
            max_cmc_volume_24h=env_float("MAX_CMC_VOLUME_24H", 0),
            enable_max_cmc_volume=env_bool("ENABLE_MAX_CMC_VOLUME", False),
            timeframe=env_str("TIMEFRAME", "4h"),
            check_interval_seconds=env_int("CHECK_INTERVAL_SECONDS", 900),
            scan_delay_seconds=env_float("SCAN_DELAY_SECONDS", 0.10),
            max_coins=env_int("MAX_COINS", 300),
            candle_limit=env_int("CANDLE_LIMIT", 200),
            cooldown_hours=env_float("COOLDOWN_HOURS", 4),
            use_closed_candle=env_bool("USE_CLOSED_CANDLE", True),
            quote_currency=env_str("QUOTE_CURRENCY", "USDT").upper(),
            exchanges=tuple(item.lower() for item in env_list("EXCHANGES", "gateio,kucoin,mexc")),
            excluded_coins=env_list("EXCLUDED_COINS", "BTC,ETH,BNB,SOL"),
            excluded_stablecoins=env_list(
                "EXCLUDED_STABLECOINS",
                "USDT,USDC,BUSD,DAI,TUSD,FDUSD,USDE,USDP,GUSD,USDD,PYUSD,FRAX",
            ),
            exchange_timeout_ms=env_int("EXCHANGE_TIMEOUT_MS", 20_000),
            exchange_retries=env_int("EXCHANGE_RETRIES", 2),
            rsi_period=env_int("RSI_PERIOD", 14),
            stoch_period=env_int("STOCH_PERIOD", 14),
            k_smoothing=env_int("K_SMOOTHING", 3),
            d_smoothing=env_int("D_SMOOTHING", 3),
            max_stoch_k=env_float("MAX_STOCH_K", 20),
            max_stoch_d=env_float("MAX_STOCH_D", 20),
            min_stoch_k=env_float("MIN_STOCH_K", 0),
            min_stoch_d=env_float("MIN_STOCH_D", 0),
            require_bullish_cross=env_bool("REQUIRE_BULLISH_CROSS", True),
            require_k_rising=env_bool("REQUIRE_K_RISING", True),
            require_d_rising=env_bool("REQUIRE_D_RISING", False),
            timezone=env_str("TIMEZONE", "Asia/Riyadh"),
            log_level=env_str("LOG_LEVEL", "INFO").upper(),
            state_file=Path(env_str("STATE_FILE", "alert_state.json")),
            show_tradingview_link=env_bool("SHOW_TRADINGVIEW_LINK", True),
            show_cmc_volume=env_bool("SHOW_CMC_VOLUME", True),
            show_stoch_values=env_bool("SHOW_STOCH_VALUES", True),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        errors: list[str] = []

        if not self.cmc_api_key:
            errors.append("CMC_API_KEY غير موجود")
        if self.enable_telegram_alerts and not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN غير موجود")
        if self.enable_telegram_alerts and not self.telegram_chat_id:
            errors.append("TELEGRAM_CHAT_ID غير موجود")
        if not self.exchanges:
            errors.append("EXCHANGES لا يحتوي على أي منصة")
        if self.cmc_limit < 1 or self.cmc_limit > 5000:
            errors.append("CMC_LIMIT يجب أن يكون بين 1 و5000")
        if self.max_coins < 1:
            errors.append("MAX_COINS يجب أن يكون أكبر من صفر")
        if self.candle_limit < 40:
            errors.append("CANDLE_LIMIT يجب ألا يقل عن 40")
        if min(self.rsi_period, self.stoch_period, self.k_smoothing, self.d_smoothing) < 1:
            errors.append("فترات Stoch RSI يجب أن تكون أكبر من صفر")
        if self.min_stoch_k > self.max_stoch_k:
            errors.append("MIN_STOCH_K لا يمكن أن يكون أكبر من MAX_STOCH_K")
        if self.min_stoch_d > self.max_stoch_d:
            errors.append("MIN_STOCH_D لا يمكن أن يكون أكبر من MAX_STOCH_D")
        if self.check_interval_seconds < 10:
            errors.append("CHECK_INTERVAL_SECONDS يجب ألا يقل عن 10 ثوانٍ")
        if self.cooldown_hours < 0:
            errors.append("COOLDOWN_HOURS لا يمكن أن يكون سالبًا")
        if self.enable_max_cmc_volume and self.max_cmc_volume_24h <= 0:
            errors.append("فعّل حد الفوليوم الأعلى بقيمة MAX_CMC_VOLUME_24H أكبر من صفر")

        if errors:
            raise ValueError("أخطاء في المتغيرات:\n- " + "\n- ".join(errors))

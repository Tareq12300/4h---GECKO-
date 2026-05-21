import os
import time
import threading
import requests
import pandas as pd
from flask import Flask

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CMC_API_KEY = os.getenv("CMC_API_KEY")

TRADE_MODE = os.getenv("TRADE_MODE", "both").lower()
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))

CMC_TOP_N = int(os.getenv("CMC_TOP_N", "1000"))
MAX_MARKET_CAP = float(os.getenv("MAX_MARKET_CAP", "100000000"))

SCALP_TIMEFRAME = os.getenv("SCALP_TIMEFRAME", "15m")
SCALP_STOCH_RSI_MAX = float(os.getenv("SCALP_STOCH_RSI_MAX", "30"))
SCALP_VOLUME_RATIO = float(os.getenv("SCALP_VOLUME_RATIO", "1.0"))

SWING_TIMEFRAME = os.getenv("SWING_TIMEFRAME", "4h")
SWING_STOCH_RSI_MAX = float(os.getenv("SWING_STOCH_RSI_MAX", "30"))
SWING_VOLUME_RATIO = float(os.getenv("SWING_VOLUME_RATIO", "1.0"))

ENABLE_BYBIT = os.getenv("ENABLE_BYBIT", "true").lower() == "true"

sent_signals = set()

STABLECOINS = {
    "USDT", "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDD",
    "USDE", "PYUSD", "FRAX", "LUSD", "GUSD", "USDJ", "USDP",
    "SUSD", "EURS", "EURT", "USTC", "MIM", "USDX"
}

MEME_COINS = {
    "DOGE", "SHIB", "PEPE", "FLOKI", "BONK", "WIF", "BRETT",
    "MEME", "TURBO", "POPCAT", "MOG", "BOME", "PONKE", "NEIRO",
    "WOJAK", "BABYDOGE", "ELON", "SAMO", "LADYS", "SNEK",
    "CATE", "AIDOGE", "COQ", "MYRO", "MAGA", "TRUMP"
}

GAMBLING_COINS = {
    "FUN", "WIN", "ROLL", "BET", "BC", "RAKE", "LOTTO", "DICE"
}

PREDICTION_MARKET_COINS = {
    "POLY", "POLK", "POLS", "SX", "GNO", "UMA", "REP", "TRUMP"
}

GAMING_COINS = {
    "AXS", "SAND", "MANA", "GALA", "ENJ", "PIXEL", "BEAM",
    "YGG", "ILV", "MAGIC", "ALICE", "TLM", "SLP", "GMT",
    "APE", "PYR", "NAKA", "GODS", "GHST", "VOXEL", "DAR",
    "MBOX", "HIGH", "SUPER", "UFO", "VRA"
}

EXCHANGE_COINS = {
    "BNB", "OKB", "KCS", "GT", "BGB", "HT", "CRO", "MX",
    "LEO", "WOO", "FTT", "BEST", "BTMX", "BTR"
}

EXCLUDED_SYMBOLS = (
    STABLECOINS
    | MEME_COINS
    | GAMBLING_COINS
    | PREDICTION_MARKET_COINS
    | GAMING_COINS
    | EXCHANGE_COINS
)

EXCLUDED_KEYWORDS = [
    "meme", "dog", "cat", "inu", "shiba", "pepe", "floki", "bonk",
    "gaming", "game", "games", "metaverse", "casino", "bet", "betting",
    "gambling", "prediction", "predict", "forecast", "exchange",
    "stablecoin", "usd stable", "fan token"
]

def send_telegram(message):
    try:
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("Telegram variables missing")
            return

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        requests.post(
            url,
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            },
            timeout=10
        )

    except Exception as e:
        print("Telegram Error:", e)

def is_excluded_coin(symbol, name, tags):
    symbol = str(symbol or "").upper()
    name = str(name or "").lower()
    tags_text = " ".join([str(t).lower() for t in tags or []])

    if symbol in EXCLUDED_SYMBOLS:
        return True

    combined_text = f"{name} {tags_text}"

    for keyword in EXCLUDED_KEYWORDS:
        if keyword in combined_text:
            return True

    return False

def get_cmc_symbols():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

    headers = {
        "X-CMC_PRO_API_KEY": CMC_API_KEY
    }

    params = {
        "start": 1,
        "limit": CMC_TOP_N,
        "convert": "USD"
    }

    try:
        if not CMC_API_KEY:
            print("CMC_API_KEY missing")
            return []

        response = requests.get(url, headers=headers, params=params, timeout=20)
        data = response.json().get("data", [])

        coins = []

        for coin in data:
            symbol = coin.get("symbol")
            name = coin.get("name")
            tags = coin.get("tags", [])

            if not symbol:
                continue

            if is_excluded_coin(symbol, name, tags):
                continue

            quote = coin.get("quote", {}).get("USD", {})

            market_cap = quote.get("market_cap")
            volume_24h = quote.get("volume_24h")

            if not market_cap:
                continue

            if market_cap > MAX_MARKET_CAP:
                continue

            coins.append({
                "symbol": symbol.upper(),
                "name": name,
                "market_cap": market_cap,
                "volume_24h": volume_24h or 0,
                "change_24h": quote.get("percent_change_24h") or 0
            })

        return coins

    except Exception as e:
        print("CMC Error:", e)
        return []

def timeframe_to_bybit(tf):
    mapping = {
        "1m": "1",
        "3m": "3",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "2h": "120",
        "4h": "240",
        "1d": "D"
    }

    return mapping.get(tf, "15")

def fetch_bybit_klines(symbol, timeframe):
    if not ENABLE_BYBIT:
        return None

    url = "https://api.bybit.com/v5/market/kline"

    params = {
        "category": "spot",
        "symbol": f"{symbol}USDT",
        "interval": timeframe_to_bybit(timeframe),
        "limit": 120
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        rows = data.get("result", {}).get("list", [])

        if not rows:
            return None

        rows.reverse()

        df = pd.DataFrame(
            rows,
            columns=[
                "time",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "turnover"
            ]
        )

        return df

    except Exception as e:
        print(f"Bybit Error {symbol}:", e)
        return None

def calculate_stoch_rsi(df, rsi_period=14, stoch_period=14, smooth_k=3, smooth_d=3):
    df = df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna()

    if len(df) < 40:
        return None, None

    delta = df["close"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(rsi_period).mean()
    avg_loss = loss.rolling(rsi_period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    min_rsi = rsi.rolling(stoch_period).min()
    max_rsi = rsi.rolling(stoch_period).max()

    stoch = (rsi - min_rsi) / (max_rsi - min_rsi) * 100

    k = stoch.rolling(smooth_k).mean()
    d = k.rolling(smooth_d).mean()

    if pd.isna(k.iloc[-1]) or pd.isna(d.iloc[-1]):
        return None, None

    return round(float(k.iloc[-1]), 2), round(float(d.iloc[-1]), 2)

def calculate_macd(df, fast=12, slow=26, signal=9):
    df = df.copy()
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna()

    if len(df) < 40:
        return False, None

    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()

    hist = macd_line - signal_line

    current = hist.iloc[-1]
    previous = hist.iloc[-2]

    if pd.isna(current) or pd.isna(previous):
        return False, None

    macd_ok = current > 0 and current > previous

    return macd_ok, round(float(current), 8)

def calculate_volume_ratio(df, lookback=20):
    df = df.copy()
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.dropna()

    if len(df) < lookback + 1:
        return None

    current_volume = df["volume"].iloc[-1]
    avg_volume = df["volume"].iloc[-lookback-1:-1].mean()

    if avg_volume == 0 or pd.isna(avg_volume):
        return None

    return round(float(current_volume / avg_volume), 2)

def format_money(value):
    try:
        value = float(value)

        if value >= 1_000_000_000:
            return f"${value / 1_000_000_000:.2f}B"

        if value >= 1_000_000:
            return f"${value / 1_000_000:.2f}M"

        if value >= 1_000:
            return f"${value / 1_000:.2f}K"

        return f"${value:.2f}"

    except:
        return "N/A"

def build_targets(price, mode):
    if mode == "scalping":
        targets = [1.5, 3, 5]
        stop_loss = 2
    else:
        targets = [5, 10, 15, 25, 40]
        stop_loss = 8

    lines = []

    for i, pct in enumerate(targets, start=1):
        target_price = price * (1 + pct / 100)
        lines.append(f"TP{i}: ${target_price:.8f} (+{pct}%)")

    sl_price = price * (1 - stop_loss / 100)

    return "\n".join(lines), f"${sl_price:.8f} (-{stop_loss}%)"

def scan_coin(symbol_data, timeframe, mode, stoch_limit, volume_limit):
    symbol = symbol_data["symbol"]

    df = fetch_bybit_klines(symbol, timeframe)

    if df is None or df.empty:
        return

    try:
        k, d = calculate_stoch_rsi(df)

        if k is None:
            return

        macd_ok, macd_hist = calculate_macd(df)

        if not macd_ok:
            return

        volume_ratio = calculate_volume_ratio(df)

        if volume_ratio is None:
            return

        if volume_ratio < volume_limit:
            return

        signal_key = f"{symbol}-{mode}-{timeframe}"

        if signal_key in sent_signals:
            return

        if k < stoch_limit:
            sent_signals.add(signal_key)

            price = float(pd.to_numeric(df["close"], errors="coerce").iloc[-1])

            targets_text, stop_loss_text = build_targets(price, mode)

            title = "⚡ SCALPING ALERT" if mode == "scalping" else "📈 SWING ALERT"

            message = f"""
{title}

💎 <b>{symbol}/USDT</b>
🏦 Exchange: Bybit
⏱ Timeframe: {timeframe}

💰 Price:
${price:.8f}

📉 Stoch RSI K: {k}
📉 Stoch RSI D: {d}

📊 MACD Histogram:
{macd_hist}

🔥 Volume Ratio:
{volume_ratio}x

🏦 Market Cap:
{format_money(symbol_data.get("market_cap"))}

💧 24H Volume:
{format_money(symbol_data.get("volume_24h"))}

📈 24H Change:
{round(symbol_data.get("change_24h") or 0, 2)}%

🎯 Targets:
{targets_text}

🛑 Stop Loss:
{stop_loss_text}
"""

            send_telegram(message)
            print(f"Signal Sent: {symbol} | {mode} | {timeframe}")

    except Exception as e:
        print(f"Scan Error {symbol}:", e)

def scanner_loop():
    send_telegram(
        "🚀 البوت اشتغل بنجاح\n\n"
        "✅ الشروط الحالية:\n"
        "• Scalping + Swing\n"
        "• Stoch RSI أقل من 30\n"
        "• MACD إيجابي وصاعد\n"
        "• Market Cap أقل من 100M\n"
        "• استبعاد: Meme / Gambling / Prediction / Gaming / Exchange / Stablecoins\n\n"
        "📡 بدأ فحص السوق..."
    )

    while True:
        print("Scanning Coins...")

        coins = get_cmc_symbols()

        print(f"Coins Loaded: {len(coins)}")

        for coin in coins:
            if TRADE_MODE in ["scalping", "both"]:
                scan_coin(
                    coin,
                    SCALP_TIMEFRAME,
                    "scalping",
                    SCALP_STOCH_RSI_MAX,
                    SCALP_VOLUME_RATIO
                )

            if TRADE_MODE in ["swing", "both"]:
                scan_coin(
                    coin,
                    SWING_TIMEFRAME,
                    "swing",
                    SWING_STOCH_RSI_MAX,
                    SWING_VOLUME_RATIO
                )

            time.sleep(0.2)

        print("Scan Complete")
        time.sleep(CHECK_INTERVAL)

@app.route("/")
def home():
    return "Bot Running"

threading.Thread(target=scanner_loop, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

from __future__ import annotations

import numpy as np
import pandas as pd

from models import StochRsiSnapshot


def calculate_stoch_rsi(
    closes: list[float],
    rsi_period: int,
    stoch_period: int,
    k_smoothing: int,
    d_smoothing: int,
) -> StochRsiSnapshot | None:
    """حساب Stoch RSI بطريقة Wilder ثم إرجاع آخر قيمتين مكتملتين لـ K وD."""
    minimum_length = rsi_period + stoch_period + k_smoothing + d_smoothing + 5
    if len(closes) < minimum_length:
        return None

    close = pd.Series(closes, dtype="float64")
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    average_gain = gain.ewm(
        alpha=1 / rsi_period,
        adjust=False,
        min_periods=rsi_period,
    ).mean()
    average_loss = loss.ewm(
        alpha=1 / rsi_period,
        adjust=False,
        min_periods=rsi_period,
    ).mean()

    relative_strength = average_gain / average_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + relative_strength))

    only_gains = (average_loss == 0.0) & (average_gain > 0.0)
    only_losses = (average_gain == 0.0) & (average_loss > 0.0)
    no_change = (average_gain == 0.0) & (average_loss == 0.0)
    rsi = rsi.mask(only_gains, 100.0)
    rsi = rsi.mask(only_losses, 0.0)
    rsi = rsi.mask(no_change, 50.0)

    rolling_min = rsi.rolling(stoch_period, min_periods=stoch_period).min()
    rolling_max = rsi.rolling(stoch_period, min_periods=stoch_period).max()
    denominator = (rolling_max - rolling_min).replace(0.0, np.nan)

    raw_stoch = ((rsi - rolling_min) / denominator) * 100.0
    k_line = raw_stoch.rolling(k_smoothing, min_periods=k_smoothing).mean()
    d_line = k_line.rolling(d_smoothing, min_periods=d_smoothing).mean()

    frame = pd.DataFrame({"k": k_line, "d": d_line}).dropna()
    if len(frame) < 2:
        return None

    previous = frame.iloc[-2]
    current = frame.iloc[-1]

    return StochRsiSnapshot(
        previous_k=float(previous["k"]),
        previous_d=float(previous["d"]),
        current_k=float(current["k"]),
        current_d=float(current["d"]),
    )

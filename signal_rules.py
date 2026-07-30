from __future__ import annotations

from config import Settings
from models import CmcAsset, StochRsiSnapshot


def is_buy_signal(
    asset: CmcAsset,
    stoch: StochRsiSnapshot,
    settings: Settings,
) -> bool:
    # الشرط الأول: فوليوم CoinMarketCap فقط.
    if asset.volume_24h_usd < settings.min_cmc_volume_24h:
        return False

    if (
        settings.enable_max_cmc_volume
        and asset.volume_24h_usd > settings.max_cmc_volume_24h
    ):
        return False

    # الشرط الثاني: Stoch RSI فقط.
    if not (settings.min_stoch_k <= stoch.current_k <= settings.max_stoch_k):
        return False

    if not (settings.min_stoch_d <= stoch.current_d <= settings.max_stoch_d):
        return False

    if settings.require_bullish_cross:
        bullish_cross = (
            stoch.previous_k <= stoch.previous_d
            and stoch.current_k > stoch.current_d
        )
        if not bullish_cross:
            return False

    if settings.require_k_rising and stoch.current_k <= stoch.previous_k:
        return False

    if settings.require_d_rising and stoch.current_d <= stoch.previous_d:
        return False

    return True

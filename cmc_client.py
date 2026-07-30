from __future__ import annotations

import logging
from typing import Any

import requests

from config import Settings
from models import CmcAsset


logger = logging.getLogger(__name__)


class CoinMarketCapClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "X-CMC_PRO_API_KEY": settings.cmc_api_key,
                "User-Agent": "stoch-cmc-telegram-bot/1.0",
            }
        )

    def fetch_assets(self) -> list[CmcAsset]:
        params = {
            "start": 1,
            "limit": self.settings.cmc_limit,
            "convert": self.settings.cmc_convert,
            "sort": "volume_24h",
            "sort_dir": "desc",
        }

        response = self.session.get(
            self.settings.cmc_api_url,
            params=params,
            timeout=self.settings.cmc_timeout_seconds,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()

        status = payload.get("status") or {}
        error_code = status.get("error_code", 0)
        if error_code not in (0, None):
            raise RuntimeError(
                f"خطأ CoinMarketCap {error_code}: {status.get('error_message', 'Unknown error')}"
            )

        raw_assets = payload.get("data") or []
        if isinstance(raw_assets, dict):
            raw_assets = list(raw_assets.values())

        excluded = set(self.settings.excluded_coins) | set(self.settings.excluded_stablecoins)
        deduplicated: dict[str, CmcAsset] = {}

        for item in raw_assets:
            try:
                symbol = str(item["symbol"]).upper().strip()
                if not symbol or symbol in excluded:
                    continue

                quote = item.get("quote", {}).get(self.settings.cmc_convert, {})
                volume = float(quote.get("volume_24h") or 0)

                if volume < self.settings.min_cmc_volume_24h:
                    continue
                if (
                    self.settings.enable_max_cmc_volume
                    and volume > self.settings.max_cmc_volume_24h
                ):
                    continue

                asset = CmcAsset(
                    cmc_id=int(item.get("id") or 0),
                    name=str(item.get("name") or symbol),
                    symbol=symbol,
                    slug=str(item.get("slug") or symbol.lower()),
                    rank=int(item["cmc_rank"]) if item.get("cmc_rank") else None,
                    price_usd=float(quote["price"]) if quote.get("price") is not None else None,
                    volume_24h_usd=volume,
                )

                # قد توجد مشاريع مختلفة تحمل الرمز نفسه. نحتفظ بالأعلى فوليومًا.
                current = deduplicated.get(symbol)
                if current is None or asset.volume_24h_usd > current.volume_24h_usd:
                    deduplicated[symbol] = asset
            except (KeyError, TypeError, ValueError) as exc:
                logger.debug("تم تجاهل سجل CMC غير صالح: %s", exc)

        assets = sorted(
            deduplicated.values(),
            key=lambda asset: asset.volume_24h_usd,
            reverse=True,
        )
        return assets[: self.settings.max_coins]

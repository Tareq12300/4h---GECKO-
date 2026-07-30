from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CmcAsset:
    cmc_id: int
    name: str
    symbol: str
    slug: str
    rank: int | None
    price_usd: float | None
    volume_24h_usd: float


@dataclass(frozen=True)
class MarketLocation:
    exchange_id: str
    exchange_name: str
    symbol: str


@dataclass(frozen=True)
class StochRsiSnapshot:
    previous_k: float
    previous_d: float
    current_k: float
    current_d: float

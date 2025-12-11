from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RawAPIItem(BaseModel):
    """Schema for raw API data from CoinPaprika or CoinGecko"""
    id: str = Field(..., alias="external_id")
    source_api: str  # "coinpaprika" or "coingecko"
    coin_id: str
    name: str
    symbol: str
    price_usd: float
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    percent_change_24h: Optional[float] = None
    created_at: datetime
    raw_data: dict = Field(default_factory=dict)

    class Config:
        populate_by_name = True


class RawCSVItem(BaseModel):
    """Schema for raw CSV cryptocurrency data"""
    id: str = Field(..., alias="external_id")
    symbol: str
    name: Optional[str] = None
    price_usd: float
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    percent_change_24h: Optional[float] = None
    created_at: datetime

    class Config:
        populate_by_name = True


class NormalizedRecord(BaseModel):
    """Normalized cryptocurrency record with unified schema"""
    id: str  # Unified ID: source_symbol (e.g., "coinpaprika_BTC", "coingecko_BTC", "csv_BTC")
    ticker: str  # Unified ticker symbol (e.g., "BTC", "ETH")
    name: str
    price_usd: float
    market_cap_usd: Optional[float] = None
    volume_24h_usd: Optional[float] = None
    percent_change_24h: Optional[float] = None
    source: str  # "coinpaprika", "coingecko", or "csv"
    created_at: datetime
    ingested_at: Optional[datetime] = None



from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NormalizedRecord(BaseModel):
    """Normalized cryptocurrency record schema."""
    id: str = Field(..., description="Unique identifier (source_ticker format)")
    ticker: str = Field(..., description="Cryptocurrency ticker symbol (e.g., BTC, ETH)")
    name: Optional[str] = Field(None, description="Full cryptocurrency name")
    price_usd: float = Field(..., description="Price in USD")
    market_cap_usd: Optional[float] = Field(None, description="Market capitalization in USD")
    volume_24h_usd: Optional[float] = Field(None, description="24-hour trading volume in USD")
    percent_change_24h: Optional[float] = Field(None, description="24-hour price change percentage")
    source: str = Field(..., description="Data source (coinpaprika, coingecko, csv)")
    created_at: datetime = Field(..., description="Source record creation time")
    ingested_at: Optional[datetime] = Field(None, description="When normalized record was saved")
    
    class Config:
        from_attributes = True

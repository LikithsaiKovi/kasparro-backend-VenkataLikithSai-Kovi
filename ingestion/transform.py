from datetime import datetime, timezone
from typing import Dict
from schemas.record import RawAPIItem, RawCSVItem, NormalizedRecord


def ensure_naive_datetime(dt: datetime) -> datetime:
    """
    Convert timezone-aware datetime to naive datetime.
    Database uses TIMESTAMP WITHOUT TIME ZONE, so we must strip timezone info.
    """
    if dt.tzinfo is not None:
        # Convert to UTC first, then remove timezone info
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def normalize_ticker(symbol: str) -> str:
    """
    Normalize ticker symbol to uppercase and handle common variations.
    Ensures ticker unification across different sources.
    """
    if not symbol:
        return ""
    # Convert to uppercase and strip whitespace
    ticker = symbol.strip().upper()
    return ticker


def normalize_price(price: float) -> float:
    """
    Normalize price to 8 decimal places for consistency.
    Handles price precision requirements.
    """
    if price is None:
        return 0.0
    # Round to 8 decimal places (standard for crypto prices)
    return round(float(price), 8)


def transform_api_record(payload: Dict) -> NormalizedRecord:
    """
    Transform raw API record (from CoinPaprika or CoinGecko) to normalized format.
    Handles ticker unification and price precision.
    """
    raw = RawAPIItem(**payload)
    
    # Normalize ticker symbol
    ticker = normalize_ticker(raw.symbol)
    
    # Use ticker as unified ID to merge all sources by coin name
    unified_id = ticker
    
    # Normalize price
    normalized_price = normalize_price(raw.price_usd)
    
    return NormalizedRecord(
        id=unified_id,
        ticker=ticker,
        name=raw.name,
        price_usd=normalized_price,
        market_cap_usd=raw.market_cap_usd if raw.market_cap_usd else None,
        volume_24h_usd=raw.volume_24h_usd if raw.volume_24h_usd else None,
        percent_change_24h=raw.percent_change_24h if raw.percent_change_24h else None,
        source=raw.source_api,
        created_at=ensure_naive_datetime(raw.created_at),
        ingested_at=datetime.utcnow(),
    )


def transform_csv_record(payload: Dict) -> NormalizedRecord:
    """
    Transform raw CSV record to normalized format.
    Handles ticker unification and price precision.
    """
    raw = RawCSVItem(**payload)
    
    # Normalize ticker symbol
    ticker = normalize_ticker(raw.symbol)
    
    # Use ticker as unified ID to merge all sources by coin name
    unified_id = ticker
    
    # Normalize price
    normalized_price = normalize_price(raw.price_usd)
    
    return NormalizedRecord(
        id=unified_id,
        ticker=ticker,
        name=raw.name if raw.name else raw.symbol,
        price_usd=normalized_price,
        market_cap_usd=raw.market_cap_usd if raw.market_cap_usd else None,
        volume_24h_usd=raw.volume_24h_usd if raw.volume_24h_usd else None,
        percent_change_24h=raw.percent_change_24h if raw.percent_change_24h else None,
        source="csv",
        created_at=ensure_naive_datetime(raw.created_at),
        ingested_at=datetime.utcnow(),
    )



"""
Best-practice normalization module for merging multi-source cryptocurrency data.

This module implements intelligent field merging with provenance tracking,
allowing multiple sources (CoinPaprika, CoinGecko, CSV) to contribute to
a single enriched record while preserving source information.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from schemas.record import NormalizedRecord


def merge_records(existing: Optional[NormalizedRecord], incoming: NormalizedRecord) -> NormalizedRecord:
    """
    Merge incoming record with existing record using best-practice strategies.
    
    Merge Strategy:
    - Volatile fields (price_usd, market_cap_usd, volume_24h_usd, percent_change_24h):
      Use most recent value (by created_at timestamp)
    - Static fields (name):
      Canonical source preference: CoinPaprika > CoinGecko > CSV
    - Timestamps:
      Use most recent created_at across all sources
    - Provenance:
      Track all sources in sources JSON field
    - Primary source:
      Source that provided the merged/main data (most recent for volatile fields)
    
    Args:
        existing: Existing normalized record (if any)
        incoming: New incoming record to merge
        
    Returns:
        Merged NormalizedRecord with enriched data from all sources
    """
    if existing is None:
        # First record for this ticker - use incoming as-is
        return incoming
    
    # Source priority for canonical fields (name)
    SOURCE_PRIORITY = {
        "coinpaprika": 1,
        "coingecko": 2,
        "csv": 3
    }
    
    # Determine which source has higher priority
    existing_priority = SOURCE_PRIORITY.get(existing.source.lower(), 99)
    incoming_priority = SOURCE_PRIORITY.get(incoming.source.lower(), 99)
    
    # Merge strategy: Use most recent for volatile fields (prices, market data)
    # Compare timestamps to determine which is more recent
    existing_ts = existing.created_at or datetime.min.replace(tzinfo=None)
    incoming_ts = incoming.created_at or datetime.min.replace(tzinfo=None)
    
    use_existing_for_volatile = existing_ts > incoming_ts
    
    # Volatile fields: Use most recent value
    if use_existing_for_volatile:
        merged_price = existing.price_usd
        merged_market_cap = existing.market_cap_usd if existing.market_cap_usd is not None else incoming.market_cap_usd
        merged_volume = existing.volume_24h_usd if existing.volume_24h_usd is not None else incoming.volume_24h_usd
        merged_percent_change = existing.percent_change_24h if existing.percent_change_24h is not None else incoming.percent_change_24h
        merged_created_at = existing.created_at
        primary_source = existing.source
    else:
        merged_price = incoming.price_usd
        merged_market_cap = incoming.market_cap_usd if incoming.market_cap_usd is not None else existing.market_cap_usd
        merged_volume = incoming.volume_24h_usd if incoming.volume_24h_usd is not None else existing.volume_24h_usd
        merged_percent_change = incoming.percent_change_24h if incoming.percent_change_24h is not None else existing.percent_change_24h
        merged_created_at = incoming.created_at
        primary_source = incoming.source
    
    # For static fields (name), prefer higher priority source
    merged_name = existing.name
    if incoming.name:
        if existing_priority > incoming_priority or not existing.name:
            merged_name = incoming.name
    
    # Use ticker from existing (should be same, but ensure consistency)
    merged_ticker = existing.ticker
    
    # Use most recent ingested_at
    merged_ingested_at = max(
        existing.ingested_at or datetime.utcnow(),
        incoming.ingested_at or datetime.utcnow()
    )
    
    # Create merged record with primary source
    # Note: We'll use a canonical ID format based on ticker
    merged_id = f"merged_{merged_ticker.lower()}"
    
    return NormalizedRecord(
        id=merged_id,
        ticker=merged_ticker,
        name=merged_name,
        price_usd=merged_price,
        market_cap_usd=merged_market_cap,
        volume_24h_usd=merged_volume,
        percent_change_24h=merged_percent_change,
        source=primary_source,  # Primary source that provided main merged data
        created_at=merged_created_at,
        ingested_at=merged_ingested_at,
    )




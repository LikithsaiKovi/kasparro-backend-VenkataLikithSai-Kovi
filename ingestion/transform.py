from datetime import datetime
from typing import Dict, Any
from schemas.record import NormalizedRecord


def normalize_ticker(ticker: str) -> str:
    """Normalize ticker symbol to uppercase."""
    return ticker.upper().strip()


def normalize_price(price: Any) -> float:
    """Normalize price to 8 decimal places."""
    try:
        return round(float(price), 8)
    except (ValueError, TypeError):
        return 0.0


def transform_api_record(payload: Dict[str, Any]) -> NormalizedRecord:
    """Transform CoinPaprika API record to normalized format."""
    coin_id = payload.get("id", "")
    symbol = payload.get("symbol", "")
    name = payload.get("name", "")
    quotes = payload.get("quotes", {})
    usd_quote = quotes.get("USD", {})
    
    ticker = normalize_ticker(symbol)
    price = normalize_price(usd_quote.get("price", 0))
    market_cap = usd_quote.get("market_cap")
    volume_24h = usd_quote.get("volume_24h")
    percent_change = usd_quote.get("percent_change_24h")
    
    created_at = datetime.utcnow()
    if "last_updated" in usd_quote:
        try:
            created_at = datetime.fromisoformat(usd_quote["last_updated"].replace("Z", "+00:00"))
            created_at = created_at.replace(tzinfo=None)
        except:
            pass
    
    return NormalizedRecord(
        id=f"coinpaprika_{coin_id}",
        ticker=ticker,
        name=name,
        price_usd=price,
        market_cap_usd=float(market_cap) if market_cap else None,
        volume_24h_usd=float(volume_24h) if volume_24h else None,
        percent_change_24h=float(percent_change) if percent_change else None,
        source="coinpaprika",
        created_at=created_at,
        ingested_at=datetime.utcnow(),
    )




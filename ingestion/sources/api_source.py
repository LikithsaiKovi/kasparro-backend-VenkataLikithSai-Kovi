import httpx
from datetime import datetime
from typing import List, Dict, Optional


async def fetch_api_records(api_source_key: str, last_id: Optional[str] = None) -> List[Dict]:
    """
    Fetch cryptocurrency data from CoinPaprika and CoinGecko APIs.
    Returns a list of dictionaries matching RawAPIItem schema.
    
    Args:
        api_source_key: API key (currently unused, but kept for future use)
        last_id: Optional checkpoint ID for resuming from a specific point
        
    Returns:
        List of dictionaries with keys: external_id, source_api, coin_id, name, symbol,
        price_usd, market_cap_usd, volume_24h_usd, percent_change_24h, created_at, raw_data
    """
    records: List[Dict] = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Fetch from CoinPaprika
        try:
            paprika_url = "https://api.coinpaprika.com/v1/tickers"
            response = await client.get(paprika_url)
            response.raise_for_status()
            paprika_data = response.json()
            
            for item in paprika_data[:50]:  # Limit to top 50 coins
                if not item.get("symbol") or not item.get("quotes", {}).get("USD"):
                    continue
                    
                usd_quote = item["quotes"]["USD"]
                coin_id = item.get("id", "")
                symbol = item.get("symbol", "").upper()
                external_id = f"coinpaprika_{coin_id}"
                
                # Skip if we're resuming and this ID is <= last_id
                if last_id and external_id <= last_id:
                    continue
                
                record = {
                    "external_id": external_id,
                    "source_api": "coinpaprika",
                    "coin_id": coin_id,
                    "name": item.get("name", symbol),
                    "symbol": symbol,
                    "price_usd": float(usd_quote.get("price", 0)),
                    "market_cap_usd": float(usd_quote.get("market_cap", 0)) if usd_quote.get("market_cap") else None,
                    "volume_24h_usd": float(usd_quote.get("volume_24h", 0)) if usd_quote.get("volume_24h") else None,
                    "percent_change_24h": float(usd_quote.get("percent_change_24h", 0)) if usd_quote.get("percent_change_24h") else None,
                    "created_at": datetime.utcnow().isoformat(),
                    "raw_data": item,
                }
                records.append(record)
        except Exception as e:
            # Log error but continue to try CoinGecko
            pass
        
        # Fetch from CoinGecko
        try:
            coingecko_url = "https://api.coingecko.com/api/v3/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 50,
                "page": 1,
            }
            response = await client.get(coingecko_url, params=params)
            response.raise_for_status()
            coingecko_data = response.json()
            
            for item in coingecko_data:
                if not item.get("symbol"):
                    continue
                    
                coin_id = item.get("id", "")
                symbol = item.get("symbol", "").upper()
                external_id = f"coingecko_{coin_id}"
                
                # Skip if we're resuming and this ID is <= last_id
                if last_id and external_id <= last_id:
                    continue
                
                record = {
                    "external_id": external_id,
                    "source_api": "coingecko",
                    "coin_id": coin_id,
                    "name": item.get("name", symbol),
                    "symbol": symbol,
                    "price_usd": float(item.get("current_price", 0)),
                    "market_cap_usd": float(item.get("market_cap", 0)) if item.get("market_cap") else None,
                    "volume_24h_usd": float(item.get("total_volume", 0)) if item.get("total_volume") else None,
                    "percent_change_24h": float(item.get("price_change_percentage_24h", 0)) if item.get("price_change_percentage_24h") else None,
                    "created_at": datetime.utcnow().isoformat(),
                    "raw_data": item,
                }
                records.append(record)
        except Exception as e:
            # Log error but return what we have
            pass
    
    return records

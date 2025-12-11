from datetime import datetime
from typing import List, Dict, Optional
import httpx


async def fetch_coinpaprika_records(api_key: Optional[str] = None, last_id: Optional[str] = None) -> List[Dict]:
    """
    Fetch cryptocurrency data from CoinPaprika API.
    CoinPaprika doesn't require an API key for basic endpoints.
    Uses /tickers endpoint for efficient batch fetching.
    """
    base_url = "https://api.coinpaprika.com/v1"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Fetch all tickers in one call (more efficient than per-coin calls)
            response = await client.get(f"{base_url}/tickers")
            response.raise_for_status()
            tickers = response.json()
            
            # Limit to top 100 coins for performance
            top_tickers = tickers[:100] if isinstance(tickers, list) else []
            
            records = []
            for ticker_data in top_tickers:
                coin_id = ticker_data.get("id")
                if not coin_id:
                    continue
                
                try:
                    record = {
                        "external_id": f"coinpaprika_{coin_id}",
                        "source_api": "coinpaprika",
                        "coin_id": coin_id,
                        "name": ticker_data.get("name", ""),
                        "symbol": ticker_data.get("symbol", "").upper(),
                        "price_usd": ticker_data.get("quotes", {}).get("USD", {}).get("price", 0.0),
                        "market_cap_usd": ticker_data.get("quotes", {}).get("USD", {}).get("market_cap", 0.0),
                        "volume_24h_usd": ticker_data.get("quotes", {}).get("USD", {}).get("volume_24h", 0.0),
                        "percent_change_24h": ticker_data.get("quotes", {}).get("USD", {}).get("percent_change_24h", 0.0),
                        "created_at": datetime.utcnow().isoformat(),
                        "raw_data": ticker_data,
                    }
                    records.append(record)
                except Exception:
                    # Skip coins that fail to process
                    continue
                    
            # Filter by last_id if provided
            if last_id:
                records = [r for r in records if r["external_id"] > last_id]
                
            return records
            
        except httpx.HTTPError as e:
            raise Exception(f"CoinPaprika API error: {str(e)}")


async def fetch_coingecko_records(api_key: Optional[str] = None, last_id: Optional[str] = None) -> List[Dict]:
    """
    Fetch cryptocurrency data from CoinGecko API.
    Free tier doesn't require API key, but has rate limits.
    """
    base_url = "https://api.coingecko.com/api/v3"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Fetch top coins by market cap
            response = await client.get(
                f"{base_url}/coins/markets",
                params={
                    "vs_currency": "usd",
                    "order": "market_cap_desc",
                    "per_page": 100,
                    "page": 1,
                    "sparkline": False,
                }
            )
            response.raise_for_status()
            coins = response.json()
            
            records = []
            for coin in coins:
                record = {
                    "external_id": f"coingecko_{coin.get('id', '')}",
                    "source_api": "coingecko",
                    "coin_id": coin.get("id", ""),
                    "name": coin.get("name", ""),
                    "symbol": coin.get("symbol", "").upper(),
                    "price_usd": coin.get("current_price", 0.0),
                    "market_cap_usd": coin.get("market_cap", 0.0),
                    "volume_24h_usd": coin.get("total_volume", 0.0),
                    "percent_change_24h": coin.get("price_change_percentage_24h", 0.0),
                    "created_at": datetime.utcnow().isoformat(),
                    "raw_data": coin,
                }
                records.append(record)
            
            # Filter by last_id if provided
            if last_id:
                records = [r for r in records if r["external_id"] > last_id]
            
            return records
            
        except httpx.HTTPError as e:
            raise Exception(f"CoinGecko API error: {str(e)}")


async def fetch_api_records(api_key: Optional[str] = None, last_id: Optional[str] = None) -> List[Dict]:
    """
    Fetch records from both CoinPaprika and CoinGecko APIs.
    Combines results from both sources.
    """
    all_records = []
    
    # Fetch from CoinPaprika
    try:
        coinpaprika_records = await fetch_coinpaprika_records(api_key, last_id)
        all_records.extend(coinpaprika_records)
    except Exception as e:
        # Log error but continue with other source
        import logging
        logging.getLogger(__name__).error(f"Failed to fetch from CoinPaprika: {e}")
    
    # Fetch from CoinGecko
    try:
        coingecko_records = await fetch_coingecko_records(api_key, last_id)
        all_records.extend(coingecko_records)
    except Exception as e:
        # Log error but continue
        import logging
        logging.getLogger(__name__).error(f"Failed to fetch from CoinGecko: {e}")
    
    return all_records



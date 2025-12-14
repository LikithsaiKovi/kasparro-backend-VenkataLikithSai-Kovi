import httpx
from typing import List, Dict, Any, Optional
from core.config import get_settings

settings = get_settings()


async def fetch_api_records(api_key: Optional[str] = None, last_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch records from CoinPaprika API.
    Returns list of payloads with external_id and full data.
    """
    try:
        # CoinPaprika API endpoint for tickers
        url = "https://api.coinpaprika.com/v1/tickers"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            
            records = []
            for item in data[:50]:  # Limit to 50 for demo
                external_id = item.get("id", "")
                records.append({
                    "external_id": external_id,
                    **item
                })
            
            return records
    except Exception as e:
        # Return empty list on error (can be logged)
        return []

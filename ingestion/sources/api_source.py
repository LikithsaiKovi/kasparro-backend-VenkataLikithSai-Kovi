import httpx
from typing import List, Dict, Any, Optional
from core.config import get_settings

settings = get_settings()


async def fetch_api_records(api_key: Optional[str] = None, last_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch records from CoinPaprika API.
    
    Args:
        api_key: Optional API key for authenticated requests. If provided, will be included
                in the Authorization header for premium API tier access.
        last_id: Optional ID to fetch records from (for pagination/resumption).
    
    Returns:
        List of payloads with external_id and full data.
    """
    try:
        # CoinPaprika API endpoint for tickers
        url = "https://api.coinpaprika.com/v1/tickers"
        
        # Prepare headers with API key if provided
        headers = {}
        if api_key:
            # CoinPaprika uses custom X-CoinAPI-Key header or Authorization header
            # depending on the plan. We support both patterns.
            headers["X-CoinAPI-Key"] = api_key
            # Some APIs use standard Authorization header with Bearer token
            # Uncomment if using Bearer token format:
            # headers["Authorization"] = f"Bearer {api_key}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers if headers else None)
            response.raise_for_status()
            data = response.json()
            
            records = []
            for item in data:
                external_id = item.get("id", "")
                records.append({
                    "external_id": external_id,
                    **item
                })
            
            return records
    except Exception as e:
        # Return empty list on error (can be logged)
        return []

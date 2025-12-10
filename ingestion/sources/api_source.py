from datetime import datetime
from typing import List, Dict, Optional


async def fetch_api_records(api_key: str, last_id: Optional[str] = None) -> List[Dict]:
    """
    Mock API fetcher. Replace API_URL with the real endpoint and apply pagination.
    last_id can be used to request only new data.
    """
    # Placeholder sample payloads; swap with real HTTP requests.
    sample = [
        {"external_id": "api-1", "title": "Alpha", "value": 10.5, "created_at": datetime.utcnow().isoformat()},
        {"external_id": "api-2", "title": "Beta", "value": 20.0, "created_at": datetime.utcnow().isoformat()},
    ]
    if last_id:
        sample = [row for row in sample if row["external_id"] > last_id]
    return sample


import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


def fetch_csv_records(path: str, last_id: Optional[str] = None) -> List[Dict]:
    """
    Read cryptocurrency CSV rows and return them as dictionaries.
    Expected CSV format:
    - symbol: Cryptocurrency ticker (e.g., BTC, ETH)
    - name: Full name (optional)
    - price_usd: Price in USD
    - market_cap_usd: Market capitalization (optional)
    - volume_24h_usd: 24h trading volume (optional)
    - percent_change_24h: 24h price change percentage (optional)
    - created_at: ISO timestamp (optional, defaults to current time)
    
    Alternative format with external_id is also supported for backwards compatibility.
    """
    csv_path = Path(path)
    if not csv_path.exists():
        return []

    records: List[Dict] = []
    with csv_path.open(encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Handle both formats: with external_id or without
            symbol = row.get("symbol") or row.get("ticker", "").strip()
            if not symbol:
                # Skip rows without symbol
                continue
            
            # Create external_id if not present
            external_id = row.get("external_id") or f"csv_{symbol.upper()}"
            
            # Parse numeric fields
            try:
                price_usd = float(row.get("price_usd", row.get("price", 0)))
            except (ValueError, TypeError):
                price_usd = 0.0
            
            try:
                market_cap_usd = float(row.get("market_cap_usd", row.get("market_cap", 0))) if row.get("market_cap_usd") or row.get("market_cap") else None
            except (ValueError, TypeError):
                market_cap_usd = None
            
            try:
                volume_24h_usd = float(row.get("volume_24h_usd", row.get("volume_24h", 0))) if row.get("volume_24h_usd") or row.get("volume_24h") else None
            except (ValueError, TypeError):
                volume_24h_usd = None
            
            try:
                percent_change_24h = float(row.get("percent_change_24h", row.get("change_24h", 0))) if row.get("percent_change_24h") or row.get("change_24h") else None
            except (ValueError, TypeError):
                percent_change_24h = None
            
            record = {
                "external_id": external_id,
                "symbol": symbol.upper(),
                "name": row.get("name", "") or symbol,
                "price_usd": price_usd,
                "market_cap_usd": market_cap_usd,
                "volume_24h_usd": volume_24h_usd,
                "percent_change_24h": percent_change_24h,
                "created_at": row.get("created_at") or datetime.utcnow().isoformat(),
            }
            records.append(record)

    if last_id:
        records = [row for row in records if row.get("external_id") and row["external_id"] > last_id]
    return records



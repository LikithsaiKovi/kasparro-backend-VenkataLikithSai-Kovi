import csv
from typing import List, Dict, Any, Optional
from pathlib import Path
from core.config import get_settings

settings = get_settings()


def fetch_csv_records(csv_path: str, last_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch records from CSV file.
    Returns list of payloads with external_id and full data.
    """
    records = []
    file_path = Path(csv_path)
    
    if not file_path.exists():
        return records
    
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            external_id = f"csv_{idx}_{row.get('symbol', 'unknown')}"
            records.append({
                "external_id": external_id,
                **row
            })
    
    return records

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


def fetch_csv_records(path: str, last_id: Optional[str] = None) -> List[Dict]:
    """
    Read CSV rows and return them as dictionaries.
    Expect columns: external_id, description, amount, created_at
    """
    csv_path = Path(path)
    if not csv_path.exists():
        return []

    records: List[Dict] = []
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["created_at"] = row.get("created_at") or datetime.utcnow().isoformat()
            records.append(row)

    if last_id:
        records = [row for row in records if row.get("external_id") and row["external_id"] > last_id]
    return records


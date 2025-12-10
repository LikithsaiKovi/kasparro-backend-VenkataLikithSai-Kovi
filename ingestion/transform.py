from datetime import datetime
from typing import Dict
from schemas.record import RawAPIItem, RawCSVItem, NormalizedRecord


def transform_api_record(payload: Dict) -> NormalizedRecord:
    raw = RawAPIItem(**payload)
    return NormalizedRecord(
        id=raw.id,
        title=raw.title,
        source="api",
        value=raw.value,
        created_at=raw.created_at,
    )


def transform_csv_record(payload: Dict) -> NormalizedRecord:
    raw = RawCSVItem(**payload)
    return NormalizedRecord(
        id=raw.id,
        title=raw.description,
        source="csv",
        value=raw.amount,
        created_at=raw.created_at,
    )


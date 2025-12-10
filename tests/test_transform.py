from datetime import datetime
from ingestion.transform import transform_api_record, transform_csv_record


def test_transform_api_record():
    payload = {
        "external_id": "api-123",
        "title": "Alpha",
        "value": 12.5,
        "created_at": datetime.utcnow().isoformat(),
    }
    record = transform_api_record(payload)
    assert record.id == "api-123"
    assert record.source == "api"
    assert record.title == "Alpha"


def test_transform_csv_record():
    payload = {
        "external_id": "csv-1",
        "description": "Gamma",
        "amount": 9.99,
        "created_at": datetime.utcnow().isoformat(),
    }
    record = transform_csv_record(payload)
    assert record.id == "csv-1"
    assert record.source == "csv"
    assert record.value == 9.99


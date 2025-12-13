import asyncio
from fastapi.testclient import TestClient
from api.main import app
from api import deps
from services import models


class FakeResult:
    def __init__(self, value=None, list_value=None):
        self.value = value
        self.list_value = list_value or []

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalars(self):
        class _Scalar:
            def __init__(self, data):
                self._data = data

            def all(self):
                return self._data

        return _Scalar(self.list_value)


class FakeSession:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.calls = 0

    async def execute(self, statement):
        self.calls += 1
        if self.calls == 1:
            return FakeResult(1)
        if "normalized_records" in str(statement):
            return FakeResult(list_value=self.rows)
        return FakeResult(None)

    async def close(self):
        return None


async def override_db():
    from datetime import datetime
    session = FakeSession(
        rows=[
            models.NormalizedRecord(
                id="BTC",  # Unified by ticker, not source_ticker
                ticker="BTC",
                name="Bitcoin",
                price_usd=45000.50,
                market_cap_usd=880000000000.0,
                volume_24h_usd=25000000000.0,
                percent_change_24h=2.5,
                source="coinpaprika",
                created_at=datetime.utcnow(),
                ingested_at=datetime.utcnow()
            )
        ]
    )
    yield session


app.dependency_overrides[deps.get_db] = override_db
client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_data_endpoint():
    resp = client.get("/data?limit=10&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert body["pagination"]["returned"] >= 0



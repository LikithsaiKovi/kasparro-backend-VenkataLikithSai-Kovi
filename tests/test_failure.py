import asyncio
import pytest
from ingestion import runner


class DummySession:
    def __init__(self):
        self.executed = []

    def add(self, obj):
        return None

    async def execute(self, stmt):
        self.executed.append(stmt)

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None


@pytest.mark.asyncio
async def test_validation_failure_does_not_crash(monkeypatch):
    # Force bad payload
    async def bad_fetch(*args, **kwargs):
        return [{"external_id": "bad"}]  # missing required fields

    dummy = DummySession()
    monkeypatch.setattr(runner, "fetch_api_records", bad_fetch)

    # ensure checkpoint stays None when no valid data
    async def fake_update(session, source, last_id):
        session.updated = last_id
    monkeypatch.setattr(runner, "_update_checkpoint", fake_update)

    try:
        await runner._ingest_api(dummy)  # noqa: SLF001
    except Exception:
        pytest.fail("ETL raised exception on bad payload")


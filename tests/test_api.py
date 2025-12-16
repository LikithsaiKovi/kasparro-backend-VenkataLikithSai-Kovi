"""Unit tests for API endpoints."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from api.main import app
from services.models import Base, NormalizedRecord
from schemas.record import NormalizedRecord as NormalizedRecordSchema


@pytest.fixture
async def test_db():
    """Create an in-memory SQLite test database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_delete=False)
    
    yield async_session
    
    await engine.dispose()


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_health_endpoint(client):
    """Test the /health endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ["ok", "healthy"]


def test_health_endpoint_structure(client):
    """Test the /health endpoint returns expected structure."""
    response = client.get("/health")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


@pytest.mark.asyncio
async def test_fetch_api_records_with_key():
    """Test that fetch_api_records can accept an API key."""
    from ingestion.sources.api_source import fetch_api_records
    
    # Mock the httpx.AsyncClient
    with patch('ingestion.sources.api_source.httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "quotes": {"USD": {"price": 45000}}
            }
        ]
        mock_response.raise_for_status = MagicMock()
        
        mock_async_client = AsyncMock()
        mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
        mock_async_client.__aexit__ = AsyncMock(return_value=None)
        mock_async_client.get = AsyncMock(return_value=mock_response)
        
        mock_client.return_value = mock_async_client
        
        result = await fetch_api_records(api_key="test_key_123", last_id=None)
        
        assert isinstance(result, list)
        assert len(result) > 0


def test_api_endpoint_returns_json(client):
    """Test that API endpoints return valid JSON."""
    response = client.get("/health")
    assert response.headers.get("content-type") is not None
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_normalized_record_schema():
    """Test that NormalizedRecordSchema validates correctly."""
    valid_data = {
        "id": "test_123",
        "ticker": "BTC",
        "name": "Bitcoin",
        "price_usd": 45000.0,
        "market_cap_usd": 880000000000.0,
        "volume_24h_usd": 25000000000.0,
        "percent_change_24h": 2.5,
        "source": "coinpaprika",
        "created_at": datetime.utcnow(),
    }
    
    record = NormalizedRecordSchema(**valid_data)
    assert record.ticker == "BTC"
    assert record.price_usd == 45000.0
    assert record.source == "coinpaprika"


@pytest.mark.asyncio
async def test_normalized_record_schema_missing_required():
    """Test that NormalizedRecordSchema validates required fields."""
    from pydantic import ValidationError
    
    incomplete_data = {
        "id": "test_123",
        "ticker": "BTC",
        # Missing required field: price_usd
        "source": "coinpaprika",
        "created_at": datetime.utcnow(),
    }
    
    with pytest.raises(ValidationError):
        NormalizedRecordSchema(**incomplete_data)

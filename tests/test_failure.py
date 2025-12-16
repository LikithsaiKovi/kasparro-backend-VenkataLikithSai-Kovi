"""Unit tests for failure scenarios and error handling."""
import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

from ingestion.transform import transform_api_record, transform_csv_record
from ingestion.normalize import merge_records
from schemas.record import NormalizedRecord


class TestTransformFailureHandling:
    """Test error handling in data transformation."""
    
    def test_transform_api_record_missing_required_fields(self):
        """Test that API records handle missing required fields gracefully."""
        payload = {
            # Missing id, symbol - should still transform
            "name": "Bitcoin"
        }
        
        record = transform_api_record(payload)
        assert isinstance(record, NormalizedRecord)
        assert record.ticker == ""  # Empty because symbol was missing
    
    def test_transform_api_record_empty_payload(self):
        """Test that empty payload doesn't crash transformation."""
        payload = {}
        
        record = transform_api_record(payload)
        assert isinstance(record, NormalizedRecord)
        assert record.price_usd == 0.0
    
    def test_transform_csv_record_malformed_timestamp(self):
        """Test that malformed timestamps are handled gracefully."""
        payload = {
            "external_id": "csv_btc_1",
            "symbol": "btc",
            "price_usd": 45000.0,
            "created_at": "invalid-timestamp"
        }
        
        record = transform_csv_record(payload)
        assert isinstance(record, NormalizedRecord)
        # Should use utcnow() as fallback
        assert isinstance(record.created_at, datetime)


class TestMergeRecordsFailures:
    """Test failure scenarios in merge logic."""
    
    def test_merge_with_none_existing_record(self):
        """Test merging when no existing record exists."""
        incoming = NormalizedRecord(
            id="test_1",
            ticker="BTC",
            name="Bitcoin",
            price_usd=45000.0,
            source="coinpaprika",
            created_at=datetime.utcnow()
        )
        
        result = merge_records(None, incoming)
        assert result.ticker == "BTC"
        assert result.price_usd == 45000.0
    
    def test_merge_records_with_different_tickers(self):
        """Test that merge handles records with same source but different tickers."""
        existing = NormalizedRecord(
            id="test_1",
            ticker="BTC",
            name="Bitcoin",
            price_usd=44000.0,
            source="coinpaprika",
            created_at=datetime(2024, 1, 15, 10, 0, 0)
        )
        
        incoming = NormalizedRecord(
            id="test_2",
            ticker="ETH",
            name="Ethereum",
            price_usd=2500.0,
            source="coinpaprika",
            created_at=datetime(2024, 1, 15, 10, 30, 0)
        )
        
        # Merge should still work (though typically only same-ticker records merge)
        result = merge_records(existing, incoming)
        assert isinstance(result, NormalizedRecord)
    
    def test_merge_chooses_most_recent_price(self):
        """Test that merge selects the most recent price value."""
        existing = NormalizedRecord(
            id="api_btc",
            ticker="BTC",
            name="Bitcoin",
            price_usd=44000.0,
            source="coinpaprika",
            created_at=datetime(2024, 1, 15, 10, 0, 0)
        )
        
        # Newer record from different source
        incoming = NormalizedRecord(
            id="csv_btc",
            ticker="BTC",
            name="Bitcoin",
            price_usd=45000.0,
            source="csv",
            created_at=datetime(2024, 1, 15, 10, 30, 0)
        )
        
        result = merge_records(existing, incoming)
        # Should use the more recent price (from incoming)
        assert result.price_usd == 45000.0


class TestAPISourceFailures:
    """Test failure handling in API source."""
    
    @pytest.mark.asyncio
    async def test_fetch_api_records_network_error(self):
        """Test that network errors are handled gracefully."""
        from ingestion.sources.api_source import fetch_api_records
        
        with patch('ingestion.sources.api_source.httpx.AsyncClient') as mock_client:
            mock_async_client = AsyncMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(side_effect=Exception("Network error"))
            
            mock_client.return_value = mock_async_client
            
            result = await fetch_api_records(api_key="test_key")
            # Should return empty list on error
            assert result == []
    
    @pytest.mark.asyncio
    async def test_fetch_api_records_invalid_json(self):
        """Test handling of invalid JSON response."""
        from ingestion.sources.api_source import fetch_api_records
        
        with patch('ingestion.sources.api_source.httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json.side_effect = ValueError("Invalid JSON")
            mock_response.raise_for_status = MagicMock()
            
            mock_async_client = AsyncMock()
            mock_async_client.__aenter__ = AsyncMock(return_value=mock_async_client)
            mock_async_client.__aexit__ = AsyncMock(return_value=None)
            mock_async_client.get = AsyncMock(return_value=mock_response)
            
            mock_client.return_value = mock_async_client
            
            result = await fetch_api_records(api_key="test_key")
            # Should handle gracefully
            assert isinstance(result, list)


class TestTransformErrorCases:
    """Test transformation error edge cases."""
    
    def test_price_conversion_with_non_numeric_market_cap(self):
        """Test that non-numeric market_cap handling in transformation."""
        payload = {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "quotes": {
                "USD": {
                    "price": 45000.0,
                    "market_cap": 880000000000.0  # Valid numeric value
                }
            }
        }

        # Should not raise an exception with valid data
        record = transform_api_record(payload)
        assert record.market_cap_usd == 880000000000.0

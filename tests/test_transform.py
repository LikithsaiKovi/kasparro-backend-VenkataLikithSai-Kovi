"""Unit tests for data transformation logic."""
import pytest
from datetime import datetime
from typing import Dict, Any

from ingestion.transform import (
    transform_api_record,
    transform_csv_record,
    normalize_ticker,
    normalize_price,
)
from schemas.record import NormalizedRecord


class TestNormalizeTickerFunction:
    """Test the ticker normalization function."""
    
    def test_normalize_ticker_lowercase(self):
        """Test that lowercase tickers are converted to uppercase."""
        result = normalize_ticker("btc")
        assert result == "BTC"
    
    def test_normalize_ticker_uppercase(self):
        """Test that uppercase tickers remain uppercase."""
        result = normalize_ticker("BTC")
        assert result == "BTC"
    
    def test_normalize_ticker_mixed_case(self):
        """Test that mixed case tickers are converted to uppercase."""
        result = normalize_ticker("EtH")
        assert result == "ETH"
    
    def test_normalize_ticker_with_spaces(self):
        """Test that spaces are stripped from tickers."""
        result = normalize_ticker("  BTC  ")
        assert result == "BTC"


class TestNormalizePriceFunction:
    """Test the price normalization function."""
    
    def test_normalize_price_integer(self):
        """Test that integer prices are converted to float."""
        result = normalize_price(45000)
        assert isinstance(result, float)
        assert result == 45000.0
    
    def test_normalize_price_float(self):
        """Test that float prices are rounded to 8 decimals."""
        result = normalize_price(45000.123456789)
        assert result == 45000.12345679
    
    def test_normalize_price_string(self):
        """Test that string prices are converted to float."""
        result = normalize_price("45000.50")
        assert isinstance(result, float)
        assert result == 45000.5
    
    def test_normalize_price_invalid_string(self):
        """Test that invalid prices return 0.0."""
        result = normalize_price("invalid")
        assert result == 0.0
    
    def test_normalize_price_none(self):
        """Test that None prices return 0.0."""
        result = normalize_price(None)
        assert result == 0.0


class TestTransformAPIRecord:
    """Test the API record transformation."""
    
    def test_transform_valid_api_record(self):
        """Test transforming a valid CoinPaprika API record."""
        payload = {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "quotes": {
                "USD": {
                    "price": 45000.0,
                    "market_cap": 880000000000.0,
                    "volume_24h": 25000000000.0,
                    "percent_change_24h": 2.5,
                    "last_updated": "2024-01-15T10:30:00Z"
                }
            }
        }
        
        record = transform_api_record(payload)
        
        assert isinstance(record, NormalizedRecord)
        assert record.ticker == "BTC"
        assert record.name == "Bitcoin"
        assert record.price_usd == 45000.0
        assert record.source == "coinpaprika"
        assert record.market_cap_usd == 880000000000.0
        assert record.volume_24h_usd == 25000000000.0
    
    def test_transform_api_record_missing_quote(self):
        """Test transforming API record with missing USD quote."""
        payload = {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "quotes": {}
        }
        
        record = transform_api_record(payload)
        
        assert record.ticker == "BTC"
        assert record.price_usd == 0.0
    
    def test_transform_api_record_sets_source(self):
        """Test that API transformation sets source to 'coinpaprika'."""
        payload = {
            "id": "ethereum",
            "symbol": "eth",
            "name": "Ethereum",
            "quotes": {
                "USD": {
                    "price": 2500.0
                }
            }
        }
        
        record = transform_api_record(payload)
        assert record.source == "coinpaprika"


class TestTransformCSVRecord:
    """Test the CSV record transformation."""
    
    def test_transform_valid_csv_record(self):
        """Test transforming a valid CSV record."""
        payload = {
            "external_id": "csv_btc_1",
            "symbol": "btc",
            "name": "Bitcoin",
            "price_usd": 45000.0,
            "market_cap_usd": 880000000000.0,
            "volume_24h_usd": 25000000000.0,
            "percent_change_24h": 2.5,
            "created_at": "2024-01-15T10:30:00Z"
        }
        
        record = transform_csv_record(payload)
        
        assert isinstance(record, NormalizedRecord)
        assert record.ticker == "BTC"
        assert record.name == "Bitcoin"
        assert record.price_usd == 45000.0
        assert record.source == "csv"
    
    def test_transform_csv_record_missing_price(self):
        """Test transforming CSV record without price field."""
        payload = {
            "external_id": "csv_btc_1",
            "symbol": "btc",
            "name": "Bitcoin"
        }
        
        record = transform_csv_record(payload)
        
        assert record.ticker == "BTC"
        assert record.price_usd == 0.0
    
    def test_transform_csv_record_sets_source(self):
        """Test that CSV transformation sets source to 'csv'."""
        payload = {
            "external_id": "csv_eth_1",
            "symbol": "eth",
            "name": "Ethereum",
            "price_usd": 2500.0
        }
        
        record = transform_csv_record(payload)
        assert record.source == "csv"
    
    def test_transform_csv_record_optional_fields(self):
        """Test that optional fields are handled correctly."""
        payload = {
            "external_id": "csv_btc_1",
            "symbol": "btc",
            "name": "Bitcoin",
            "price_usd": 45000.0,
            "market_cap_usd": None,
            "volume_24h_usd": None,
            "percent_change_24h": None
        }
        
        record = transform_csv_record(payload)
        assert record.market_cap_usd is None
        assert record.volume_24h_usd is None
        assert record.percent_change_24h is None

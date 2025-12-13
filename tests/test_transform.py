from datetime import datetime
from ingestion.transform import transform_api_record, transform_csv_record


def test_transform_api_record_coinpaprika():
    payload = {
        "external_id": "coinpaprika_btc-bitcoin",
        "source_api": "coinpaprika",
        "coin_id": "btc-bitcoin",
        "name": "Bitcoin",
        "symbol": "BTC",
        "price_usd": 45000.50,
        "market_cap_usd": 880000000000.0,
        "volume_24h_usd": 25000000000.0,
        "percent_change_24h": 2.5,
        "created_at": datetime.utcnow().isoformat(),
        "raw_data": {},
    }
    record = transform_api_record(payload)
    assert record.id == "BTC"  # Unified by ticker, not source_ticker
    assert record.source == "coinpaprika"
    assert record.ticker == "BTC"
    assert record.name == "Bitcoin"
    assert record.price_usd == 45000.50
    assert record.market_cap_usd == 880000000000.0


def test_transform_api_record_coingecko():
    payload = {
        "external_id": "coingecko_ethereum",
        "source_api": "coingecko",
        "coin_id": "ethereum",
        "name": "Ethereum",
        "symbol": "eth",
        "price_usd": 2800.75,
        "market_cap_usd": 337000000000.0,
        "volume_24h_usd": 12000000000.0,
        "percent_change_24h": 1.8,
        "created_at": datetime.utcnow().isoformat(),
        "raw_data": {},
    }
    record = transform_api_record(payload)
    assert record.id == "ETH"  # Unified by ticker, not source_ticker
    assert record.source == "coingecko"
    assert record.ticker == "ETH"  # Should be normalized to uppercase
    assert record.name == "Ethereum"
    assert record.price_usd == 2800.75


def test_transform_csv_record():
    payload = {
        "external_id": "csv_BTC",
        "symbol": "BTC",
        "name": "Bitcoin",
        "price_usd": 45000.50,
        "market_cap_usd": 880000000000.0,
        "volume_24h_usd": 25000000000.0,
        "percent_change_24h": 2.5,
        "created_at": datetime.utcnow().isoformat(),
    }
    record = transform_csv_record(payload)
    assert record.id == "BTC"  # Unified by ticker, not source_ticker
    assert record.source == "csv"
    assert record.ticker == "BTC"
    assert record.name == "Bitcoin"
    assert record.price_usd == 45000.50


def test_ticker_unification():
    """Test that ticker symbols are normalized to uppercase"""
    payload_upper = {
        "external_id": "coinpaprika_btc",
        "source_api": "coinpaprika",
        "coin_id": "btc",
        "name": "Bitcoin",
        "symbol": "BTC",
        "price_usd": 45000.50,
        "created_at": datetime.utcnow().isoformat(),
        "raw_data": {},
    }
    payload_lower = {
        "external_id": "coingecko_btc",
        "source_api": "coingecko",
        "coin_id": "bitcoin",
        "name": "Bitcoin",
        "symbol": "btc",
        "price_usd": 45001.00,
        "created_at": datetime.utcnow().isoformat(),
        "raw_data": {},
    }
    
    record1 = transform_api_record(payload_upper)
    record2 = transform_api_record(payload_lower)
    
    # Both should have uppercase ticker
    assert record1.ticker == "BTC"
    assert record2.ticker == "BTC"



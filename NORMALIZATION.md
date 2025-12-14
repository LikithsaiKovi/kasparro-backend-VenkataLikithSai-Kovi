# Best-Practice Multi-Source Normalization Implementation

## Overview
Replaced "unification by overwrite" (last-writer-wins) with intelligent multi-source record merging that preserves provenance while creating enriched unified records.

## What Changed

### 1. **Database Schema Enhancement** ([services/models.py](services/models.py))
   - **Removed:** Single `source` field
   - **Added:** 
     - `sources` (JSON): Stores all source data with timestamps
       ```json
       {
         "coinpaprika": {"price_usd": 45000, "created_at": "...", "ingested_at": "..."},
         "coingecko": {"price_usd": 45100, "created_at": "...", "ingested_at": "..."},
         "csv": {"price_usd": 45050, "created_at": "...", "ingested_at": "..."}
       }
       ```
     - `primary_source`: Which source provided the merged/main data
   - **Benefit:** Complete provenance tracking - you can see which source each field came from

### 2. **Pydantic Schema Update** ([schemas/record.py](schemas/record.py))
   - Updated `NormalizedRecord` to match new database schema with `sources` dict and `primary_source`

### 3. **New Normalization Module** ([ingestion/normalize.py](ingestion/normalize.py)) - *NEW FILE*
   Implements intelligent field merging with these strategies:
   
   **For volatile price fields** (price_usd, market_cap_usd, volume_24h_usd, percent_change_24h):
   - Use most recent value (by `created_at` timestamp)
   - Rationale: Prices change constantly, most recent = most accurate
   
   **For static fields** (name):
   - Canonical source preference: CoinPaprika > CoinGecko > CSV
   - Rationale: Some sources are more authoritative/standardized
   
   **For timestamps:**
   - Use most recent `created_at` across all sources
   - Rationale: Reflects when data was last updated
   
   **Provenance Tracking:**
   - All source data preserved in JSON
   - `primary_source` tracks which source provided the main merged data

### 4. **Transform Functions Simplified** ([ingestion/transform.py](ingestion/transform.py))
   - No longer handle merging (that's done in runner)
   - Just normalize individual records and mark their source
   - Creates transformation records with empty `sources` dict (populated during merge)

### 5. **Runner Merge Logic** ([ingestion/runner.py](ingestion/runner.py))
   **OLD approach:**
   ```python
   DELETE FROM normalized_records WHERE ticker = 'BTC'
   INSERT INTO normalized_records VALUES (...)
   ```
   ❌ Loses all historical multi-source data

   **NEW approach:**
   ```python
   1. Fetch existing record for ticker
   2. Call merge_records(existing, incoming)
   3. Merge intelligently selects best values per field
   4. UPDATE single record with merged data + provenance
   ```
   ✅ Preserves all source data, enriches record

## Example: How Merging Works

**Initial state:** No BTC record

Ingestion 1: CoinPaprika provides BTC
```
price: $45,000 (CoinPaprika)
market_cap: $880B (CoinPaprika)
volume: $25B (CoinPaprika)
sources: {coinpaprika: {price_usd: 45000, ...}}
primary_source: coinpaprika
```

Ingestion 2: CoinGecko provides newer BTC data
```
price: $45,100 (CoinGecko, more recent created_at)
market_cap: $875B (CoinGecko, more recent)
volume: $26B (CoinGecko, more recent)
sources: {
  coinpaprika: {price_usd: 45000, created_at: '10:00', ...},
  coingecko: {price_usd: 45100, created_at: '10:30', ...}
}
primary_source: coingecko
```

Ingestion 3: CSV provides older BTC data
```
price: $44,950 (ignored - CoinGecko is more recent)
market_cap: $876B (ignored - CoinGecko is more recent)
volume: $25.5B (ignored - CoinGecko is more recent)
sources: {
  coinpaprika: {price_usd: 45000, created_at: '10:00', ...},
  coingecko: {price_usd: 45100, created_at: '10:30', ...},
  csv: {price_usd: 44950, created_at: '09:00', ...}
}
primary_source: coingecko (still - it has the most recent data)
```

**Result:** Single BTC record with:
- Best price from most recent source (CoinGecko)
- Full provenance showing all sources contributed
- No data loss - all source records kept in JSON

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Multi-source handling** | Overwrite/lose data | Merge intelligently |
| **Provenance** | Lost | Preserved in JSON |
| **Data enrichment** | Single source value | Multiple sources per field |
| **Historical tracking** | None | Can query which sources updated when |
| **Best practices** | ❌ | ✅ Standard data warehouse approach |

## Backward Compatibility Notes

⚠️ **Breaking change:** The `NormalizedRecord` model changed:
- Old: `source: str` (single value)
- New: `sources: dict` (all sources) + `primary_source: str`

**Migration path:**
- Run `python ingestion/runner.py --init-db` to create new schema
- Existing normalized records can be re-ingested for full provenance
- API responses should handle new JSON `sources` field

## Testing

To test multi-source merging:
```bash
# Run ETL to populate with real data
python ingestion/runner.py --once

# Check normalized records now have provenance
python -c "
from services.db import SessionLocal
from services import models
session = SessionLocal()
record = session.query(models.NormalizedRecord).first()
print(f'Ticker: {record.ticker}')
print(f'Price: {record.price_usd}')
print(f'Sources: {record.sources}')
print(f'Primary: {record.primary_source}')
"
```

Expected output:
```
Ticker: BTC
Price: 45100.0
Sources: {'coinpaprika': {...}, 'coingecko': {...}, 'csv': {...}}
Primary: coingecko
```

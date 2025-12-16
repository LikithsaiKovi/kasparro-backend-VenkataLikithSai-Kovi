# Best-Practice Multi-Source Normalization Implementation

## Overview
Implements intelligent multi-source record merging using a "most recent by timestamp" strategy for volatile fields and source priority for static fields. One record per ticker is maintained in the database, with a single canonical `source` field indicating which source provided the merged data.

## What Changed

### 1. **Database Schema** ([services/models.py](services/models.py))
   - `NormalizedRecord` table maintains one record per ticker
   - `source` field (string): Indicates which source provided the primary/merged data
   - Fields: `id`, `ticker`, `name`, `price_usd`, `market_cap_usd`, `volume_24h_usd`, `percent_change_24h`, `source`, `created_at`, `ingested_at`
   - **Note:** Full multi-source provenance tracking (JSON) is not currently implemented. Current implementation uses a single `source` field.
   - **Benefit:** Simple, production-proven approach that prevents duplicate records while maintaining data freshness

### 2. **Pydantic Schema** ([schemas/record.py](schemas/record.py))
   - `NormalizedRecord` model matches the database schema
   - Fields align with the single-source normalization approach

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

### 4. **Transform Functions** ([ingestion/transform.py](ingestion/transform.py))
   - Normalize individual records from each source
   - Mark source in each record
   - Transformation is independent per source

### 5. **Runner Merge Logic** ([ingestion/runner.py](ingestion/runner.py))
   **Merge approach:**
   ```python
   1. Fetch existing record by ticker
   2. Call merge_records(existing, incoming)
   3. Merge intelligently selects best values per field
   4. Delete old record and insert merged record with canonical ID
   ```
   ✅ Maintains single record per ticker while selecting best data from all sources

## Example: How Merging Works

**Initial state:** No BTC record

Ingestion 1: CoinPaprika provides BTC
```
price: $45,000 (CoinPaprika)
market_cap: $880B (CoinPaprika)
volume: $25B (CoinPaprika)
source: coinpaprika
```

Ingestion 2: CoinGecko provides newer BTC data
```
price: $45,100 (CoinGecko, more recent created_at)
market_cap: $875B (CoinGecko, more recent)
volume: $26B (CoinGecko, more recent)
source: coingecko (updated because it has more recent data)
```

Ingestion 3: CSV provides older BTC data
```
price: $44,950 (ignored - CoinGecko is more recent)
market_cap: $876B (ignored - CoinGecko is more recent)
volume: $25.5B (ignored - CoinGecko is more recent)
source: coingecko (unchanged - still has the most recent data)
```

**Result:** Single BTC record with:
- Best price from most recent source (CoinGecko)
- Source field tracks which source provided the merged data
- No duplicate records per ticker

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Multi-source handling** | Overwrite/lose data | Merge intelligently |
| **Data freshness** | Last source wins | Most recent data used |
| **Record management** | Multiple per ticker | One canonical record |
| **Source tracking** | Lost | Preserved in source field |
| **Best practices** | ❌ | ✅ Production-proven approach |

## Current Implementation Status

✅ **Implemented:**
- Single record per ticker using merge logic
- Most recent price selection strategy
- Source priority for static fields (name)
- Canonical ID format: `merged_{ticker}`
- Single source tracking

⚠️ **Not Currently Implemented (Future Enhancement):**
- Full JSON provenance tracking (storing all historical source data)
- This would be added to extend the current system if complete audit trail is needed

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
record = session.query(models.NormalizedRecord).filter_by(ticker='BTC').first()
if record:
    print(f'Ticker: {record.ticker}')
    print(f'Price: {record.price_usd}')
    print(f'Source: {record.source}')
    print(f'Created: {record.created_at}')
"
```

Expected output:
```
Ticker: BTC
Price: 45100.0
Source: coingecko
Created: 2024-01-15 10:30:00
```

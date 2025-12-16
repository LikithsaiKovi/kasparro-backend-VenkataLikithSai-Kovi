# Testing Best-Practice Normalization

This guide explains how to test the multi-source normalization feature that intelligently merges data from CoinPaprika, CoinGecko, and CSV sources.

## What is Best-Practice Normalization?

Instead of "last writer wins" (overwriting), the system now:
- **Merges** data from multiple sources intelligently
- **Preserves** the best value for each field based on source priority and recency
- **Enriches** records by combining data from all sources

## Merge Strategy

### Volatile Fields (Price Data)
- **Fields:** `price_usd`, `market_cap_usd`, `volume_24h_usd`, `percent_change_24h`
- **Strategy:** Use most recent value (by `created_at` timestamp)
- **Rationale:** Prices change constantly; most recent = most accurate

### Static Fields
- **Fields:** `name`
- **Strategy:** Canonical source preference: CoinPaprika > CoinGecko > CSV
- **Rationale:** Some sources have more standardized/authoritative names

### Primary Source
- Tracks which source provided the main merged data (the one with most recent timestamp)

## Testing Steps

### Step 1: Start the System

```bash
docker-compose up --build
```

Wait for services to be ready:
- Database: "ready to accept connections"
- API: "Uvicorn running on http://0.0.0.0:8000"

---

### Step 2: Verify Initial State (No Data)

```bash
curl http://localhost:8000/data?limit=5
```

**Expected:** Empty data array (or existing data if previously run)

---

### Step 3: Trigger ETL to Ingest from Multiple Sources

```bash
curl -X POST http://localhost:8000/trigger-etl -H "X-Scheduler-Token: YOUR_TOKEN"
```

**Wait 30-45 seconds** for ETL to process data from:
- CoinPaprika API
- CSV file

---

### Step 4: Check Normalized Records

```bash
curl http://localhost:8000/data?limit=10
```

**What to Verify:**
1. ✅ Records have `ticker` normalized to uppercase (BTC, ETH, etc.)
2. ✅ Each ticker appears **only once** (unified across sources)
3. ✅ `source` field shows which source provided the primary data
4. ✅ `id` field uses format: `merged_{ticker}` (e.g., `merged_btc`)

---

### Step 5: Verify Merging Logic

#### 5.1 Check a Specific Ticker

```bash
curl "http://localhost:8000/data?ticker=BTC"
```

**Expected Result:**
- Only ONE BTC record (not multiple)
- `source` field shows the primary source
- Price data reflects the most recent source

#### 5.2 Check Raw Data (to see all sources)

Connect to database:
```bash
docker exec -it kasparro-backend-db-1 psql -U postgres -d postgres
```

Run queries:
```sql
-- Check raw API records for BTC
SELECT external_id, ingested_at FROM raw_api_records 
WHERE payload::text LIKE '%BTC%' OR payload::text LIKE '%Bitcoin%' 
LIMIT 5;

-- Check raw CSV records for BTC
SELECT external_id, ingested_at FROM raw_csv_records 
WHERE payload::text LIKE '%BTC%' OR payload::text LIKE '%Bitcoin%' 
LIMIT 5;

-- Check normalized BTC record (should be ONE record)
SELECT id, ticker, name, price_usd, source, created_at, ingested_at 
FROM normalized_records 
WHERE ticker = 'BTC';
```

**Expected:**
- Multiple raw records (from different sources)
- **Only ONE normalized record** with merged data

#### 5.3 Exit PostgreSQL
```sql
\q
```

---

### Step 6: Test Merging with Multiple Ingestions

#### 6.1 First ETL Run (CoinPaprika data)

```bash
curl -X POST http://localhost:8000/trigger-etl -H "X-Scheduler-Token: YOUR_TOKEN"
```

Wait 30 seconds, then check:
```bash
curl "http://localhost:8000/data?ticker=BTC"
```

**Note the:**
- `price_usd` value
- `source` (should be "coinpaprika")
- `created_at` timestamp

#### 6.2 Second ETL Run (CSV data - may have different price)

```bash
curl -X POST http://localhost:8000/trigger-etl -H "X-Scheduler-Token: YOUR_TOKEN"
```

Wait 30 seconds, then check again:
```bash
curl "http://localhost:8000/data?ticker=BTC"
```

**Verify:**
- ✅ Still **only ONE BTC record** (merged, not duplicate)
- ✅ `price_usd` should reflect the **most recent** source
- ✅ `source` field shows which source had the most recent data
- ✅ If CSV has newer timestamp, price should update
- ✅ If CSV has older timestamp, price should remain from CoinPaprika

---

### Step 7: Verify Source Priority for Name Field

Check records where CSV might have a different name format:

```bash
curl "http://localhost:8000/data?ticker=BTC" | python -m json.tool
```

**Verify:**
- ✅ `name` field uses CoinPaprika format (if available)
- ✅ If only CSV has name, it uses CSV name
- ✅ Priority: CoinPaprika > CoinGecko > CSV

---

### Step 8: Database-Level Verification

```bash
docker exec -it kasparro-backend-db-1 psql -U postgres -d postgres
```

```sql
-- Count records by source in raw tables
SELECT 'API' as source_type, COUNT(*) as count FROM raw_api_records
UNION ALL
SELECT 'CSV' as source_type, COUNT(*) as count FROM raw_csv_records;

-- Count normalized records (should be fewer - unified by ticker)
SELECT COUNT(*) as normalized_count FROM normalized_records;

-- Check for duplicate tickers (should be ZERO)
SELECT ticker, COUNT(*) as count 
FROM normalized_records 
GROUP BY ticker 
HAVING COUNT(*) > 1;

-- View sample merged records
SELECT ticker, name, price_usd, source, created_at 
FROM normalized_records 
ORDER BY ticker 
LIMIT 10;
```

**Expected Results:**
- ✅ Raw records: Multiple (one per source)
- ✅ Normalized records: Fewer (one per ticker)
- ✅ No duplicate tickers (all merged)
- ✅ Each ticker has merged data

```sql
\q
```

---

## Test Scenarios

### Scenario 1: First Source Wins (No Existing Data)

1. Clear database: `docker-compose down -v` (removes volumes)
2. Start fresh: `docker-compose up --build`
3. Trigger ETL: First source creates the record
4. Verify: Record exists with first source data

### Scenario 2: Newer Source Updates Price

1. CoinPaprika provides BTC at $45,000 (timestamp: 10:00)
2. CSV provides BTC at $44,900 (timestamp: 09:00)
3. **Expected:** BTC record shows $45,000 (most recent)
4. **Source:** "coinpaprika" (provided most recent data)

### Scenario 3: Older Source Doesn't Overwrite

1. CSV provides BTC at $44,900 (timestamp: 09:00) - already exists
2. CoinPaprika provides BTC at $45,000 (timestamp: 10:00)
3. **Expected:** BTC record shows $45,000 (most recent wins)
4. CSV data doesn't overwrite newer CoinPaprika data

### Scenario 4: Missing Fields Filled from Other Source

1. CoinPaprika provides: price, name (but no market_cap)
2. CSV provides: price, market_cap (but older timestamp)
3. **Expected:**
   - Price: CoinPaprika (more recent)
   - Market Cap: CSV (fills missing field)
   - Name: CoinPaprika (higher priority source)

---

## Verification Checklist

### ✅ Unification
- [ ] Each ticker appears only once in normalized_records
- [ ] No duplicate tickers after multiple ETL runs
- [ ] ID format is `merged_{ticker}`

### ✅ Merging Logic
- [ ] Most recent price data is used (by created_at)
- [ ] Name uses canonical source preference (CoinPaprika > CSV)
- [ ] Missing fields filled from other sources
- [ ] `source` field reflects primary source (most recent)

### ✅ Data Preservation
- [ ] Raw data preserved (raw_api_records, raw_csv_records)
- [ ] All sources contribute to merged record
- [ ] No data loss during merging

### ✅ Data Quality
- [ ] Tickers normalized to uppercase
- [ ] Prices normalized to 8 decimal places
- [ ] Valid timestamps
- [ ] No NULL values where data should exist

---

## Expected JSON Response Example

After merging multiple sources for BTC:

```json
{
  "data": [
    {
      "id": "merged_btc",
      "ticker": "BTC",
      "name": "Bitcoin",
      "price_usd": 45000.50000000,
      "market_cap_usd": 880000000000.0,
      "volume_24h_usd": 25000000000.0,
      "percent_change_24h": 2.5,
      "source": "coinpaprika",
      "created_at": "2025-12-14T10:30:00Z",
      "ingested_at": "2025-12-14T10:35:00Z"
    }
  ],
  "pagination": {...},
  "meta": {...}
}
```

**Key Points:**
- ✅ `id`: `merged_btc` (unified ID, not source-specific)
- ✅ `ticker`: `BTC` (normalized uppercase)
- ✅ `source`: Shows primary source (most recent data)
- ✅ Only ONE record per ticker

---

## Troubleshooting

### Issue: Multiple records per ticker
**Solution:** Check that `_upsert_normalized` uses merge logic, not direct insert

### Issue: Wrong price used
**Solution:** Verify `created_at` timestamps in raw data. Most recent should win.

### Issue: Name not from preferred source
**Solution:** Check source priority order in `merge_records()` function

---

## SQL Queries for Advanced Testing

```sql
-- Find all sources that contributed to BTC
SELECT DISTINCT 
  (SELECT COUNT(*) FROM raw_api_records WHERE payload::text LIKE '%BTC%') as api_count,
  (SELECT COUNT(*) FROM raw_csv_records WHERE payload::text LIKE '%BTC%') as csv_count,
  (SELECT COUNT(*) FROM normalized_records WHERE ticker = 'BTC') as normalized_count;

-- Compare prices across sources (if stored in raw payloads)
-- This would require parsing JSON, but shows the concept

-- Check merge behavior: most recent should be primary source
SELECT ticker, source, price_usd, created_at 
FROM normalized_records 
ORDER BY ticker, created_at DESC;
```

---

## Summary

The best-practice normalization ensures:
1. ✅ **One record per ticker** (unified across sources)
2. ✅ **Intelligent merging** (most recent for prices, canonical for names)
3. ✅ **No data loss** (raw data preserved, best values merged)
4. ✅ **Source tracking** (primary source reflects most recent data)

This is superior to simple overwrite because:
- Preserves data quality (uses best value, not just latest)
- Maintains provenance (know which source provided primary data)
- Enriches records (combines data from multiple sources)
- Follows data warehouse best practices




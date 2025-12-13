# Database Migration Guide

## Normalization ID Format Change

The normalization system was updated to use ticker-based IDs (e.g., "BTC") instead of source_ticker format (e.g., "coinpaprika_BTC"). This unifies all sources by coin name.

### Issue
Old database records may still have IDs in the format `{source}_{ticker}` (e.g., "coinpaprika_BTC", "coingecko_BTC"). New records use just the ticker (e.g., "BTC").

### Migration Steps

If you have existing data with old ID format, you need to migrate:

```sql
-- Option 1: Clean migration (recommended for fresh deployments)
-- Delete old records and re-run ETL
TRUNCATE TABLE normalized_records;
TRUNCATE TABLE etl_checkpoints;
-- Then re-run ETL to populate with new format

-- Option 2: Update existing records
-- Update IDs from old format to new format
UPDATE normalized_records 
SET id = ticker 
WHERE id LIKE 'coinpaprika_%' OR id LIKE 'coingecko_%' OR id LIKE 'csv_%';

-- Note: This may cause conflicts if multiple sources exist for same ticker
-- In that case, keep the most recent record:
WITH ranked AS (
  SELECT id, ticker, source, ingested_at,
         ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY ingested_at DESC) as rn
  FROM normalized_records
  WHERE id LIKE 'coinpaprika_%' OR id LIKE 'coingecko_%' OR id LIKE 'csv_%'
)
DELETE FROM normalized_records 
WHERE id IN (
  SELECT id FROM ranked WHERE rn > 1
);

-- Then update remaining records
UPDATE normalized_records 
SET id = ticker 
WHERE id LIKE 'coinpaprika_%' OR id LIKE 'coingecko_%' OR id LIKE 'csv_%';
```

### Verification

After migration, verify:
```sql
-- All IDs should be just ticker symbols (no underscores with source prefix)
SELECT DISTINCT id FROM normalized_records WHERE id LIKE '%_%';
-- Should return empty or only legitimate multi-word tickers

-- Check for unified records
SELECT ticker, COUNT(*) as sources 
FROM normalized_records 
GROUP BY ticker 
HAVING COUNT(*) > 1;
-- Should show coins with multiple sources unified into one record
```


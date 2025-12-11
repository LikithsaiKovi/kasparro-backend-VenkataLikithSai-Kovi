#!/usr/bin/env bash
set -euo pipefail

# start.sh - launches ETL runner in background then FastAPI app

# Apply any pending migrations (placeholder; alembic optional)
python -m ingestion.runner --init-db

# Start ETL runner in the background
python -m ingestion.runner --once &

# Start FastAPI via uvicorn
exec uvicorn api.main:app --host 0.0.0.0 --port 8000



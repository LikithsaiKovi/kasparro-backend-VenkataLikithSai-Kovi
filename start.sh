#!/usr/bin/env bash
set -euo pipefail

# start.sh - launches ETL runner in background then FastAPI app

echo "Starting Kasparro ETL Backend..."

# Initialize database (with retry logic for Railway)
echo "Initializing database..."
MAX_RETRIES=5
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python -m ingestion.runner --init-db 2>&1; then
        echo "Database initialized successfully"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "Database initialization failed, retrying ($RETRY_COUNT/$MAX_RETRIES)..."
            sleep 2
        else
            echo "Warning: Database initialization failed after $MAX_RETRIES attempts"
            echo "Continuing anyway - API will start but ETL may fail"
        fi
    fi
done

# Start ETL runner in the background (don't fail if this fails)
echo "Starting ETL runner in background..."
python -m ingestion.runner --once || echo "Warning: ETL runner failed, continuing..." &

# Start FastAPI via uvicorn
echo "Starting FastAPI server..."
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}






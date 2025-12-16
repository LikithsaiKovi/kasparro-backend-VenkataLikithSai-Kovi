#!/usr/bin/env bash
set -euo pipefail

# start.sh - Initialize database and launch FastAPI app with integrated ETL scheduler

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
            echo "Continuing anyway - API will start but may have issues"
        fi
    fi
done

# Start FastAPI via uvicorn (ETL scheduler is integrated into the app)
echo "Starting FastAPI server with integrated ETL scheduler..."
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}










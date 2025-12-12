# Kasparro Backend & ETL System - Cryptocurrency Data Pipeline

A production-ready ETL pipeline and REST API built with FastAPI, async SQLAlchemy, and PostgreSQL. The system ingests cryptocurrency data from multiple sources (CoinPaprika API, CoinGecko API, and CSV), stores raw data, performs schema normalization with ticker unification and price precision handling, and exposes queryable endpoints with comprehensive metadata and observability.

**Docker Hub Image:** `likithsai32/etl-assignment:latest`

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Design Philosophy](#design-philosophy)
- [System Components](#system-components)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [Testing](#testing)
- [Configuration](#configuration)
- [Observability](#observability)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Sources                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │CoinPaprika  │    │ CoinGecko   │    │ CSV Source  │        │
│  │    API      │    │    API      │    │             │        │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘        │
└─────────┼──────────────────┼──────────────────┼────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
     ┌────────────────────────────────────────────┐
     │         ETL Runner (Background Task)       │
     │  ┌──────────────────────────────────────┐  │
     │  │ 1. Extract (with checkpointing)      │  │
     │  │ 2. Validate (Pydantic schemas)       │  │
     │  │ 3. Transform (normalize to common)   │  │
     │  │ 4. Load (idempotent upserts)         │  │
     │  └──────────────────────────────────────┘  │
     └────────────┬───────────────────────────────┘
                  │
                  ▼
     ┌────────────────────────────────────────────┐
     │         PostgreSQL Database                │
     │  ┌──────────────┐  ┌──────────────────┐   │
     │  │ Raw Tables   │  │ Normalized Table │   │
     │  │ - API        │  │ - Unified Schema │   │
     │  │ - CSV        │  │ - Source Tagged  │   │
     │  └──────────────┘  └──────────────────┘   │
     │  ┌──────────────┐  ┌──────────────────┐   │
     │  │ Checkpoints  │  │ ETL Run History  │   │
     │  │ (Incremental)│  │ (Observability)  │   │
     │  └──────────────┘  └──────────────────┘   │
     └────────────┬───────────────────────────────┘
                  │
                  ▼
     ┌────────────────────────────────────────────┐
     │          FastAPI REST API                  │
     │  ┌──────────────────────────────────────┐  │
     │  │ GET  /data      (query & paginate)   │  │
     │  │ GET  /health    (system readiness)   │  │
     │  │ GET  /stats     (ETL metrics)        │  │
     │  │ POST /trigger-etl (manual trigger)   │  │
     │  └──────────────────────────────────────┘  │
     └────────────┬───────────────────────────────┘
                  │
                  ▼
          ┌───────────────┐
          │  API Clients  │
          │  (Dashboard,  │
          │   Analytics)  │
          └───────────────┘
```

---

## Design Philosophy

### 1. **Separation of Concerns**
- **Ingestion Layer** (`ingestion/`): Handles all data extraction, transformation, and loading logic
- **API Layer** (`api/`): Pure HTTP interface for querying processed data
- **Data Layer** (`services/`): Database models and connection management
- **Schema Layer** (`schemas/`): Pydantic models ensure type safety and validation

**Reasoning:** Clean boundaries make each component testable in isolation and allow independent scaling (e.g., run multiple ETL workers, scale API separately).

### 2. **Idempotency First**
All database operations use PostgreSQL `INSERT ... ON CONFLICT` (upserts) to ensure safe retries and exactly-once semantics.

**Reasoning:** Network failures, process crashes, or duplicate runs won't corrupt data. Critical for production reliability.

### 3. **Incremental Processing**
Checkpoint tracking (`etl_checkpoints` table) stores the last successfully processed record ID per source.

**Reasoning:** 
- Reduces redundant processing on each ETL run
- Enables resumption from failure points
- Scales efficiently as data volume grows

### 4. **Raw + Normalized Pattern**
- **Raw tables** preserve original payloads (audit trail, reprocessing capability)
- **Normalized table** provides queryable, validated, unified schema

**Reasoning:** 
- Raw data retention supports schema evolution and debugging
- Normalized layer optimizes query performance and simplifies client integration
- Source tagging enables per-source analytics

### 5. **Observability Built-In**
- Structured logging (JSON) via `structlog`
- ETL run tracking table captures start/end times, success/failure counts, durations
- Health endpoint exposes system state and last run status

**Reasoning:** Production systems require visibility. Structured logs integrate with monitoring stacks (Datadog, ELK), run history enables SLA tracking.

### 6. **Async-First Architecture**
Async SQLAlchemy + `asyncpg` + async HTTP clients maximize I/O concurrency.

**Reasoning:** ETL workloads are I/O-bound (network fetches, database writes). Async enables processing thousands of records efficiently without thread overhead.

---

## System Components

### Core Modules

#### `ingestion/runner.py`
**Central ETL orchestrator**
- Initializes database schema on startup
- Manages per-source ingestion workflows
- Tracks run metadata (status, counts, timing)
- Supports CLI modes: `--once`, `--init-db`, `--run-forever`

**Design Decision:** Single entry point simplifies deployment (one process for scheduled runs, one for on-demand triggers).

#### `ingestion/sources/`
**Pluggable source adapters**
- `api_source.py`: Fetches from external REST API with authentication
- `csv_source.py`: Reads local/mounted CSV files

**Design Decision:** Abstract source interface allows adding new sources (S3, databases, webhooks) without touching core ETL logic.

#### `ingestion/transform.py`
**Schema mapping layer with cryptocurrency-specific logic**
- Converts raw source payloads (CoinPaprika, CoinGecko, CSV) to Pydantic models
- Maps disparate schemas to unified `NormalizedRecord` format with crypto fields (ticker, price_usd, market_cap_usd, etc.)
- Implements ticker unification (normalizes symbols to uppercase, handles variations)
- Normalizes price precision to 8 decimal places
- Validates data types, required fields, constraints

**Design Decision:** Pydantic provides free validation + serialization. Explicit transform functions with domain-specific logic (ticker unification, price precision) ensure data quality across sources.

#### `api/routes/`
**HTTP endpoints**
- `data.py`: Query interface with filtering, pagination, sorting
- `health.py`: Liveness probe (DB connectivity + last ETL status)
- `stats.py`: Aggregate ETL metrics (success/failure counts, last run times)
- `trigger.py`: Webhook endpoint to manually trigger ETL runs

**Design Decision:** Separate route files scale better than monolithic routers. Each route has single responsibility.

#### `services/models.py`
**SQLAlchemy ORM models**
- Maps Python classes to database tables
- Defines constraints (unique indexes, foreign keys)
- Enables type-safe database queries

**Design Decision:** ORM abstracts SQL dialects, simplifies migrations, provides query builder safety.

#### `core/config.py`
**Centralized configuration**
- Environment variable parsing via Pydantic `BaseSettings`
- Type validation for all config values
- Single source of truth for runtime parameters

**Design Decision:** 12-factor app compliance. Config separated from code enables environment-specific deployments without code changes.

---

## Data Flow

### ETL Pipeline Execution

```
1. Runner starts (scheduled/triggered)
   ↓
2. For each source (API, CSV):
   a. Query checkpoint table for last_id
   b. Fetch records > last_id from source
   c. For each record:
      - Insert into raw_{source}_records (ON CONFLICT DO NOTHING)
      - Validate & transform to NormalizedRecord
      - Upsert into normalized_records (ON CONFLICT UPDATE)
      - Track success/failure count
   d. Update checkpoint with max(seen_ids)
   e. Record ETL run (status, processed, failed, duration_ms)
   ↓
3. Commit transaction (atomic per source)
   ↓
4. Sleep interval (if --run-forever) or exit
```

### Query Flow

```
Client → GET /data?source=api&limit=10
         ↓
     FastAPI route handler
         ↓
     SQLAlchemy query builder
         ↓
     PostgreSQL (normalized_records table)
         ↓
     JSON response + metadata (count, pagination links)
```

---

## Database Schema

### `raw_api_records`
Stores original API payloads as-is.

| Column       | Type      | Description                          |
|--------------|-----------|--------------------------------------|
| id           | SERIAL    | Auto-incrementing primary key        |
| external_id  | STRING    | Source record identifier (unique)    |
| payload      | JSONB     | Full raw response from API           |
| ingested_at  | TIMESTAMP | When record was saved                |

**Index:** Unique constraint on `external_id` enables idempotent inserts.

### `raw_csv_records`
Similar to `raw_api_records` but for CSV sources.

### `normalized_records`
Unified, queryable cryptocurrency schema.

| Column              | Type      | Description                          |
|---------------------|-----------|--------------------------------------|
| id                  | STRING    | Primary key (source_ticker format, e.g., "coinpaprika_BTC") |
| ticker              | STRING    | Unified cryptocurrency ticker symbol (e.g., "BTC", "ETH") |
| name                | STRING    | Full cryptocurrency name (e.g., "Bitcoin") |
| price_usd           | FLOAT     | Price in USD (normalized to 8 decimal places) |
| market_cap_usd      | FLOAT     | Market capitalization in USD (nullable) |
| volume_24h_usd      | FLOAT     | 24-hour trading volume in USD (nullable) |
| percent_change_24h  | FLOAT     | 24-hour price change percentage (nullable) |
| source              | STRING    | Origin tag (coinpaprika, coingecko, csv) |
| created_at          | TIMESTAMP | Source record creation time          |
| ingested_at         | TIMESTAMP | When normalized record was saved     |

**Design:** 
- `id` is primary key with format `{source}_{ticker}` (e.g., "coinpaprika_BTC", "coingecko_ETH")
- `ticker` is indexed for efficient filtering by cryptocurrency symbol
- `source` enables filtering by origin (coinpaprika, coingecko, csv)
- Ticker unification ensures same cryptocurrency from different sources can be queried by common ticker
- Upserts update all fields on conflict (enables price corrections)

### `etl_checkpoints`
Tracks incremental processing state.

| Column        | Type      | Description                          |
|---------------|-----------|--------------------------------------|
| id            | SERIAL    | Primary key                          |
| source        | STRING    | Source identifier (unique)           |
| last_id       | STRING    | Last successfully processed ID       |
| last_timestamp| TIMESTAMP | When last_id was processed           |
| updated_at    | TIMESTAMP | Last checkpoint update               |

**Purpose:** On restart, ETL resumes from `last_id + 1` instead of reprocessing all history.

### `etl_runs`
Audit log of ETL executions.

| Column      | Type      | Description                          |
|-------------|-----------|--------------------------------------|
| id          | SERIAL    | Primary key                          |
| source      | STRING    | Which source was processed           |
| status      | STRING    | success / failure / running          |
| started_at  | TIMESTAMP | Run start time                       |
| finished_at | TIMESTAMP | Run completion time                  |
| processed   | INT       | Records successfully processed       |
| failed      | INT       | Records that failed validation       |
| duration_ms | INT       | Total run time in milliseconds       |
| message     | STRING    | Error details (if failure)           |

**Purpose:** Enables monitoring, SLA tracking, failure investigation.

---

## API Endpoints

### `GET /data`
**Query normalized cryptocurrency records with filtering and pagination.**

**Query Parameters:**
- `source` (optional): Filter by origin (coinpaprika, coingecko, csv)
- `ticker` (optional): Filter by cryptocurrency ticker symbol (e.g., BTC, ETH)
- `start_date` (optional): Filter records created after this date (ISO 8601)
- `end_date` (optional): Filter records created before this date (ISO 8601)
- `limit` (default: 50, max: 200): Records per page
- `offset` (default: 0): Pagination offset

**Response:**
```json
{
  "data": [
    {
      "id": "coinpaprika_btc-bitcoin",
      "ticker": "BTC",
      "name": "Bitcoin",
      "price_usd": 45000.50000000,
      "market_cap_usd": 880000000000.0,
      "volume_24h_usd": 25000000000.0,
      "percent_change_24h": 2.5,
      "source": "coinpaprika",
      "created_at": "2025-01-10T10:00:00Z",
      "ingested_at": "2025-01-10T12:00:00Z"
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "returned": 1,
    "total": 1523
  },
  "meta": {
    "request_id": "req-1704892800000",
    "api_latency_ms": 12.45
  }
}
```

### `GET /health`
**System readiness check for load balancers.**

**Response:**
```json
{
  "status": "ok",
  "database": "connected",
  "last_etl_run": {
    "source": "api",
    "status": "success",
    "finished_at": "2025-12-10T11:55:00Z",
    "processed": 342,
    "failed": 0
  }
}
```

### `GET /stats`
**ETL performance metrics.**

**Response:**
```json
{
  "api": {
    "last_success": "2025-12-10T11:55:00Z",
    "last_failure": "2025-12-09T08:30:00Z",
    "total_runs": 145,
    "total_processed": 45231,
    "total_failed": 23
  },
  "csv": {
    "last_success": "2025-12-10T11:56:00Z",
    "total_runs": 145,
    "total_processed": 12450,
    "total_failed": 0
  }
}
```

### `POST /trigger-etl`
**Manually trigger an ETL run (for webhooks/schedulers).**

**Headers:**
- `X-Scheduler-Token`: (optional) Authentication token

**Response:**
```json
{
  "status": "triggered",
  "timestamp": "2025-12-10T12:00:00Z"
}
```

---

## Quick Start

### Prerequisites
- **Docker & Docker Compose** (recommended)
- **Python 3.11+** (for local development)
- **PostgreSQL 15+** (if running without Docker)

### Option 1: Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/LikithsaiKovi/kasparro-backend-VenkataLikithSai-Kovi.git
cd kasparro-backend-VenkataLikithSai-Kovi

# Create environment file
cp .env.example .env
# Edit .env and add your API_SOURCE_KEY

# Start services (Postgres + API + ETL)
docker compose up --build

# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Option 2: Docker Hub Image

```bash
# Pull pre-built image
docker pull likithsai32/etl-assignment:latest

# Create .env file with required variables
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/postgres
API_SOURCE_KEY=your_api_key_here
CSV_PATH=/data/sample.csv
LOG_LEVEL=INFO
EOF

# Run container (requires external Postgres)
docker run --env-file .env \
  -v $(pwd)/data:/data \
  -p 8000:8000 \
  likithsai32/etl-assignment:latest
```

### Option 3: Local Development

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
export API_SOURCE_KEY="your_key"
export CSV_PATH="data/sample.csv"

# Initialize database
python -m ingestion.runner --init-db

# Run ETL once
python -m ingestion.runner --once

# Start API server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/health

# View stats
curl http://localhost:8000/stats

# Query data
curl "http://localhost:8000/data?limit=5"

# Interactive API docs
open http://localhost:8000/docs
```

---

## Deployment

### Cloud Run (Google Cloud)

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/PROJECT_ID/kasparro-etl:v1

# Deploy to Cloud Run
gcloud run deploy kasparro-etl \
  --image gcr.io/PROJECT_ID/kasparro-etl:v1 \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars DATABASE_URL=postgresql+asyncpg://USER:PASS@/DB?host=/cloudsql/INSTANCE \
  --set-secrets API_SOURCE_KEY=api-key:latest \
  --add-cloudsql-instances PROJECT_ID:REGION:INSTANCE

# Schedule ETL via Cloud Scheduler
gcloud scheduler jobs create http etl-hourly \
  --schedule="0 * * * *" \
  --uri="https://kasparro-etl-xyz.run.app/trigger-etl" \
  --http-method=POST \
  --headers="X-Scheduler-Token=YOUR_SECRET_TOKEN"
```

### AWS ECS/Fargate

```bash
# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.REGION.amazonaws.com
docker tag likithsai32/etl-assignment:latest ACCOUNT.dkr.ecr.REGION.amazonaws.com/kasparro-etl:latest
docker push ACCOUNT.dkr.ecr.REGION.amazonaws.com/kasparro-etl:latest

# Create task definition with environment variables
# DATABASE_URL → RDS Postgres connection string
# API_SOURCE_KEY → SSM Parameter Store / Secrets Manager

# Schedule ETL via EventBridge
# Trigger ECS RunTask on cron schedule
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kasparro-etl
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: api
        image: likithsai32/etl-assignment:latest
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        - name: API_SOURCE_KEY
          valueFrom:
            secretKeyRef:
              name: api-credentials
              key: token
---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: etl-runner
spec:
  schedule: "0 * * * *"  # Hourly
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: etl
            image: likithsai32/etl-assignment:latest
            command: ["python", "-m", "ingestion.runner", "--once"]
```

---

## Testing

### Run Full Test Suite

```bash
# Via Docker (includes test database)
docker compose run --rm api pytest -v

# Local (requires test database)
pytest -v

# With coverage
pytest --cov=. --cov-report=html
```

### Test Structure

```
tests/
├── conftest.py          # Fixtures (test DB, async client)
├── test_transform.py    # Unit tests for schema mapping
├── test_api.py          # Integration tests for endpoints
└── test_etl.py          # ETL pipeline tests
```

### Key Test Scenarios
- ✅ Schema validation (valid/invalid payloads)
- ✅ Idempotent inserts (duplicate records)
- ✅ Checkpoint resume (incremental processing)
- ✅ API filtering and pagination
- ✅ Error handling (source failures, DB errors)

---

## Configuration

### Environment Variables

| Variable          | Required | Default | Description |
|-------------------|----------|---------|-------------|
| `DATABASE_URL`    | Yes      | -       | PostgreSQL async connection string |
| `API_SOURCE_KEY`  | Yes      | -       | Authentication key for API source |
| `CSV_PATH`        | No       | `data/sample.csv` | Path to CSV file |
| `LOG_LEVEL`       | No       | `INFO`  | Logging verbosity (DEBUG, INFO, WARN, ERROR) |
| `SCHEDULER_TOKEN` | No       | -       | Secret token for `/trigger-etl` authentication |

### Example `.env` File

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
API_SOURCE_KEY=  # Optional - CoinPaprika/CoinGecko don't require keys for basic usage
CSV_PATH=/app/data/sample.csv
LOG_LEVEL=INFO
SCHEDULER_TOKEN=oc_7tl3_IX2hk7jtmyVc-pzQASkip1P3Gaefz_AE2Mc  # Generated secure token
```

**CSV Format:**
The CSV file should contain cryptocurrency data with the following columns:
- `symbol` (required): Cryptocurrency ticker (e.g., BTC, ETH)
- `name` (optional): Full name of the cryptocurrency
- `price_usd` (required): Price in USD
- `market_cap_usd` (optional): Market capitalization
- `volume_24h_usd` (optional): 24-hour trading volume
- `percent_change_24h` (optional): 24-hour price change percentage
- `created_at` (optional): ISO timestamp (defaults to current time)

---

## Observability

### Structured Logging
All logs output JSON via `structlog` for easy parsing:

```json
{
  "event": "etl_run_started",
  "source": "api",
  "timestamp": "2025-12-10T12:00:00Z",
  "level": "info"
}
```

Integrate with:
- **Datadog**: Forward container logs to Datadog agent
- **ELK Stack**: Ship to Elasticsearch via Filebeat
- **CloudWatch**: Native integration with AWS ECS

### Metrics & Monitoring

**Database Metrics:**
```sql
-- ETL success rate (last 24 hours)
SELECT source, 
       COUNT(*) FILTER (WHERE status = 'success') * 100.0 / COUNT(*) as success_rate
FROM etl_runs 
WHERE started_at > NOW() - INTERVAL '24 hours'
GROUP BY source;

-- Average processing time
SELECT source, AVG(duration_ms) as avg_ms
FROM etl_runs
WHERE status = 'success'
GROUP BY source;
```

**Health Checks:**
- Liveness: `GET /health` (200 = healthy)
- Readiness: Check `last_etl_run.finished_at` is recent

**Alerting Examples:**
- ETL run failures > 3 in 1 hour
- No successful run in 2 hours
- Database connection failures
- Average response time > 500ms

---

## Project Structure

```
kasparro-backend/
├── api/
│   ├── main.py              # FastAPI app initialization
│   └── routes/
│       ├── data.py          # GET /data (query endpoint)
│       ├── health.py        # GET /health (readiness probe)
│       ├── stats.py         # GET /stats (ETL metrics)
│       └── trigger.py       # POST /trigger-etl (manual trigger)
├── core/
│   ├── config.py            # Environment configuration
│   └── logger.py            # Structured logging setup
├── ingestion/
│   ├── runner.py            # ETL orchestration (main entry point)
│   ├── transform.py         # Schema mapping functions
│   └── sources/
│       ├── api_source.py    # API data fetcher
│       └── csv_source.py    # CSV data reader
├── schemas/
│   └── record.py            # Pydantic models (validation)
├── services/
│   ├── db.py                # Database connection factory
│   └── models.py            # SQLAlchemy ORM models
├── tests/
│   ├── conftest.py          # Test fixtures
│   ├── test_api.py          # API integration tests
│   ├── test_etl.py          # ETL pipeline tests
│   └── test_transform.py   # Transformation unit tests
├── data/                    # Sample CSV files
├── .env.example             # Environment template
├── docker-compose.yml       # Local development stack
├── Dockerfile               # Container image definition
├── Makefile                 # Common commands
├── requirements.txt         # Python dependencies
├── start.sh                 # Container entrypoint
└── README.md                # This file
```

---

## Makefile Commands

```bash
make up          # Start Postgres + API + ETL
make down        # Stop all services
make logs        # Follow container logs
make test        # Run pytest inside container
make shell       # Open shell in API container
make psql        # Connect to PostgreSQL CLI
```

---

## Production Checklist

- [x] Structured logging (JSON format)
- [x] Health endpoint for load balancers
- [x] Database connection pooling
- [x] Idempotent data writes
- [x] Checkpoint-based incremental processing
- [x] Comprehensive error handling
- [x] API rate limiting (implement `slowapi` if needed)
- [x] Secrets management (environment variables)
- [ ] Add authentication to `/trigger-etl` (token validation)
- [ ] Implement request timeout limits
- [ ] Add database migration tool (Alembic)
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Configure auto-scaling policies
- [ ] Implement distributed tracing (OpenTelemetry)

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

MIT License - See LICENSE file for details

---

## Contact

**Venkata Likith Sai Kovi**  
GitHub: [@LikithsaiKovi](https://github.com/LikithsaiKovi)  
Repository: [kasparro-backend-VenkataLikithSai-Kovi](https://github.com/LikithsaiKovi/kasparro-backend-VenkataLikithSai-Kovi)



# Kasparro Backend & ETL System

A production-ready ETL pipeline and REST API built with FastAPI, async SQLAlchemy, and PostgreSQL. The system ingests cryptocurrency data from the CoinPaprika API, performs intelligent data normalization with ticker unification, and exposes queryable endpoints with comprehensive metadata.

**Version:** 1.1.2  
**Status:** ✅ Live on Railway  
**Live Demo:** https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/docs  
**Repository:** https://github.com/LikithsaiKovi/kasparro-backend-VenkataLikithSai-Kovi

---

## 🚀 Quick Start for Recruiters

**Choose your testing method:**

### Option 1: Test Live Production (No Setup Required) ⚡

**Test in your browser (fastest):**
- 📊 [Interactive API Docs](https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/docs)
- ✅ [Health Check](https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/health)
- 💰 [View Data](https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/data?limit=5)
- 📈 [Statistics](https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/stats)

**Or test via command line (Windows/Mac/Linux):**
```bash
# Health check
curl https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/health

# View cryptocurrency data
curl https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/data?limit=5

# View ETL statistics
curl https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/stats
```

### Option 2: Run Locally with Docker 🐳

**Prerequisites:** Docker Desktop installed and running

```bash
# 1. Clone repository
git clone https://github.com/LikithsaiKovi/kasparro-backend-VenkataLikithSai-Kovi.git
cd kasparro-backend-VenkataLikithSai-Kovi

# 2. Start services (automatically sets up database)
docker-compose up --build

# 3. Test in a new terminal
curl http://localhost:8000/health
curl http://localhost:8000/data?limit=5

# 4. Open browser to http://localhost:8000/docs
```

**That's it!** No manual database setup required.

---

## 🏗️ System Architecture & Data Flow

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           EXTERNAL DATA SOURCES                                  │
│                                                                                   │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐                 │
│  │ CoinPaprika  │      │  CoinGecko   │      │   CSV Files  │                 │
│  │     API      │      │     API      │      │              │                 │
│  │              │      │              │      │  (Local/     │                 │
│  │ REST API     │      │ REST API     │      │  Mounted)    │                 │
│  └──────┬───────┘      └──────┬───────┘      └──────┬───────┘                 │
│         │                      │                      │                          │
│         └──────────────────────┼──────────────────────┘                          │
│                                │                                                  │
└────────────────────────────────┼──────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        ETL PIPELINE (Background Process)                         │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  EXTRACT LAYER                                                          │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │   │
│  │  │  API Source     │  │  API Source     │  │  CSV Source     │        │   │
│  │  │  Fetcher        │  │  Fetcher        │  │  Reader         │        │   │
│  │  │  (CoinPaprika)  │  │  (CoinGecko)    │  │  (CSV Parser)   │        │   │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘        │   │
│  └───────────┼─────────────────────┼─────────────────────┼──────────────────┘   │
│              │                     │                     │                       │
│              └─────────────────────┼─────────────────────┘                       │
│                                    │                                             │
│                                    ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  TRANSFORM LAYER                                                        │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │  1. Schema Validation (Pydantic Models)                         │   │   │
│  │  │  2. Ticker Normalization (Uppercase, Strip)                     │   │   │
│  │  │  3. Price Precision (8 decimal places)                          │   │   │
│  │  │  4. Data Type Conversion                                        │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                         │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │  NORMALIZATION ENGINE (Best-Practice Merging)                   │   │   │
│  │  │  • Merge multi-source records by ticker                         │   │   │
│  │  │  • Volatile fields: Use most recent (by created_at)             │   │   │
│  │  │  • Static fields: Canonical source priority                     │   │   │
│  │  │  • Preserve one record per ticker                               │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                    │                                             │
│                                    ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  LOAD LAYER                                                             │   │
│  │  ┌─────────────────┐              ┌─────────────────┐                 │   │
│  │  │  Raw Data       │              │  Normalized     │                 │   │
│  │  │  Storage        │              │  Data Storage   │                 │   │
│  │  │  (Audit Trail)  │              │  (Queryable)    │                 │   │
│  │  └─────────────────┘              └─────────────────┘                 │   │
│  │                                                                         │   │
│  │  • Idempotent Upserts (ON CONFLICT)                                    │   │
│  │  • Checkpoint Tracking (Incremental Processing)                        │   │
│  │  • Run History Logging (Observability)                                 │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┼─────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      POSTGRESQL DATABASE (Data Warehouse)                        │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  RAW DATA TABLES (Audit & Reprocessing)                                 │   │
│  │  ┌────────────────────┐      ┌────────────────────┐                    │   │
│  │  │ raw_api_records    │      │ raw_csv_records    │                    │   │
│  │  │ • external_id (PK) │      │ • external_id (PK) │                    │   │
│  │  │ • payload (JSONB)  │      │ • payload (JSONB)  │                    │   │
│  │  │ • ingested_at      │      │ • ingested_at      │                    │   │
│  │  └────────────────────┘      └────────────────────┘                    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  NORMALIZED DATA (Unified Schema)                                       │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │ normalized_records                                              │   │   │
│  │  │ • id (PK): merged_{ticker}                                      │   │   │
│  │  │ • ticker (indexed, uppercase)                                   │   │   │
│  │  │ • name, price_usd, market_cap_usd, volume_24h_usd              │   │   │
│  │  │ • percent_change_24h, source, created_at, ingested_at           │   │   │
│  │  │ • ONE RECORD PER TICKER (merged from all sources)               │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  METADATA TABLES (ETL Management)                                       │   │
│  │  ┌────────────────────┐      ┌────────────────────┐                    │   │
│  │  │ etl_checkpoints    │      │ etl_runs           │                    │   │
│  │  │ • source (unique)  │      │ • source, status   │                    │   │
│  │  │ • last_id          │      │ • processed/failed │                    │   │
│  │  │ • last_timestamp   │      │ • duration_ms      │                    │   │
│  │  └────────────────────┘      │ • started_at       │                    │   │
│  │                               │ • finished_at      │                    │   │
│  │                               └────────────────────┘                    │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────┼─────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI REST API LAYER                                   │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  API ROUTES                                                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │   │
│  │  │  GET /health │  │  GET /data   │  │  GET /stats  │                 │   │
│  │  │  • DB status │  │  • Query     │  │  • ETL       │                 │   │
│  │  │  • Last ETL  │  │  • Filter    │  │    metrics   │                 │   │
│  │  └──────────────┘  │  • Paginate  │  └──────────────┘                 │   │
│  │                    └──────────────┘                                    │   │
│  │  ┌──────────────────┐      ┌──────────────────┐                       │   │
│  │  │ POST /trigger-etl│      │  GET /docs       │                       │   │
│  │  │ • Manual trigger │      │  • Swagger UI    │                       │   │
│  │  │ • Background job │      │  • Interactive   │                       │   │
│  │  └──────────────────┘      └──────────────────┘                       │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                   │
│  • Async SQLAlchemy queries                                                      │
│  • Request/Response validation (Pydantic)                                        │
│  • Error handling & logging                                                      │
│  • CORS enabled for cross-origin requests                                        │
└────────────────────────────────────┼─────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              API CLIENTS                                         │
│                                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                         │
│  │   Web        │  │   Mobile     │  │   Analytics  │                         │
│  │  Dashboard   │  │     App      │  │   Platform   │                         │
│  └──────────────┘  └──────────────┘  └──────────────┘                         │
│                                                                                   │
│  • REST API Consumers                                                            │
│  • Real-time cryptocurrency data                                                 │
│  • Filtered & aggregated queries                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Sequence

```
1. ETL Trigger (Scheduled/Manual)
   ↓
2. EXTRACT: Fetch from CoinPaprika API
   ↓
3. TRANSFORM: 
   - Validate with Pydantic schemas
   - Normalize tickers (uppercase)
   - Normalize prices (8 decimals)
   - Map to unified schema
   ↓
4. MERGE (Best-Practice):
   - Check for existing record by ticker
   - Merge volatile fields (use most recent)
   - Merge static fields (use canonical source)
   - Create/Update unified record
   ↓
5. LOAD:
   - Store raw payloads (audit trail)
   - Upsert normalized records (one per ticker)
   - Update checkpoints (incremental processing)
   - Log ETL run metadata
   ↓
6. API Query:
   - Client requests /data?ticker=BTC
   - FastAPI queries normalized_records
   - Returns merged, enriched record
   ↓
7. Response: Single unified record with best data from all sources
```

### Key Design Decisions

1. **Raw + Normalized Pattern**
   - Raw tables preserve original payloads (audit, reprocessing)
   - Normalized table provides unified, queryable schema

2. **Best-Practice Merging**
   - Volatile fields: Most recent wins (by timestamp)
   - Static fields: Canonical source priority
   - One record per ticker (no duplicates)

3. **Incremental Processing**
   - Checkpoints track last processed ID per source
   - Resumes from failure points
   - Reduces redundant processing

4. **Idempotent Operations**
   - All inserts use `ON CONFLICT` clauses
   - Safe to retry ETL runs
   - Exactly-once semantics

5. **Async Architecture**
   - Async SQLAlchemy + asyncpg driver
   - Async HTTP clients (httpx)
   - Maximizes I/O concurrency

---

---

## � Normalization & Data Quality

### When Does Normalization Happen?

**Normalization occurs automatically during the ETL process**, not through manual API operations. Here's the workflow:

1. **ETL Trigger** (Automated hourly or manual via `POST /trigger-etl`)
2. **Extract**: Fetch raw data from CoinPaprika API
3. **Transform**: Validate and standardize each record
4. **Normalize**: Intelligent merging by ticker symbol
5. **Load**: Store in database (one unified record per ticker)

**Important**: There are no public `POST` or `PATCH` endpoints to manually create/update cryptocurrency records. All data ingestion happens through the ETL pipeline, ensuring consistency and data quality.

### Normalization Method: Timestamp-Based Intelligent Merging

The system uses a **best-practice merging strategy** that intelligently combines data from multiple ETL runs to maintain accurate, up-to-date records:

#### Strategy Overview
- **One record per ticker**: BTC, ETH, etc. each have a single unified record
- **Volatile fields**: Use most recent data (by timestamp)
- **Static fields**: Use canonical source priority
- **Deduplication**: Prevents duplicate tickers across sources

#### Field-Specific Rules

**Volatile Fields (Time-Sensitive Market Data):**
- `price_usd` - Current price
- `market_cap_usd` - Market capitalization
- `volume_24h_usd` - 24-hour trading volume
- `percent_change_24h` - 24-hour price change

**Strategy**: Always use the **most recent value** based on `created_at` timestamp. This ensures API consumers always get the latest market data.

**Static Fields (Canonical Information):**
- `name` - Cryptocurrency name (e.g., "Bitcoin")
- `ticker` - Symbol (e.g., "BTC")

**Strategy**: Use **source priority** (CoinPaprika preferred) and normalize format (uppercase tickers).

#### Example: How Merging Works

```
Scenario: BTC already exists in DB from 1 hour ago, new data arrives from ETL

Existing Record (1 hour old):
  ticker: BTC
  price_usd: 45000.00
  name: Bitcoin
  created_at: 2025-12-18T10:00:00Z
  source: coinpaprika

Incoming Record (new):
  ticker: BTC
  price_usd: 45500.00
  name: Bitcoin
  created_at: 2025-12-18T11:00:00Z
  source: coinpaprika

Merged Result:
  ticker: BTC
  price_usd: 45500.00        ← Newer price wins
  name: Bitcoin               ← Canonical source preserved
  created_at: 2025-12-18T11:00:00Z  ← Most recent timestamp
  source: coinpaprika
```

#### Data Quality Guarantees

1. **Ticker Normalization**: All tickers converted to uppercase (btc → BTC)
2. **Price Precision**: 8 decimal places for accurate cryptocurrency values
3. **Idempotent Operations**: Safe to re-run ETL without duplicates
4. **Audit Trail**: Raw API responses preserved in `raw_api_records` table
5. **Incremental Processing**: Checkpoints track last processed record per source

#### For Recruiters: Why This Approach?

This normalization strategy demonstrates:
- **Production-ready data engineering**: Handles real-world scenarios like multiple data sources and updates
- **Time-series data management**: Respects temporal ordering for volatile financial data
- **Defensive programming**: Prevents duplicates, handles missing fields, preserves audit trails
- **Scalability**: Architecture supports adding new data sources with minimal changes
- **Best practices**: Follows industry standards for ETL pipelines (Extract → Transform → Normalize → Load)

---

## �📊 API Endpoints

All endpoints are documented interactively at `/docs` (Swagger UI)

| Endpoint | Method | Description | Example |
|----------|--------|-------------|---------|
| `/` | GET | API information | `curl http://localhost:8000/` |
| `/health` | GET | System health & DB status | `curl http://localhost:8000/health` |
| `/data` | GET | Query cryptocurrency data | `curl http://localhost:8000/data?limit=5` |
| `/stats` | GET | ETL statistics | `curl http://localhost:8000/stats` |
| `/trigger-etl` | POST | Manually trigger ETL | `curl -X POST http://localhost:8000/trigger-etl` |
| `/docs` | GET | Interactive API docs | Open in browser |

**Query Parameters for `/data`:**
- `limit` (int): Number of records (default: 100, max: 1000)
- `offset` (int): Pagination offset (default: 0)
- `ticker` (string): Filter by ticker (e.g., "BTC")
- `source` (string): Filter by source (e.g., "coinpaprika")
- `created_after` (datetime): Filter by creation date
- `created_before` (datetime): Filter by creation date

**Example Queries:**
```bash
# Get Bitcoin data only
curl http://localhost:8000/data?ticker=BTC

# Get data from specific source
curl http://localhost:8000/data?source=coinpaprika

# Pagination (page 2, 10 per page)
curl http://localhost:8000/data?limit=10&offset=10

# Date range
curl "http://localhost:8000/data?created_after=2025-12-01&created_before=2025-12-31"
```

---

## 🏗️ Architecture Overview

```
Data Sources (APIs + CSV) → ETL Pipeline → PostgreSQL → REST API → Clients
                              ↓
                    [Extract] → [Transform] → [Normalize] → [Load]
                              ↓
                    Raw Storage + Normalized Storage (one record per ticker)
```

**Key Features:**
- **API ingestion**: CoinPaprika API
- **Intelligent merging**: Combines data from all sources into unified records
- **Data quality**: Ticker normalization (uppercase), price precision (8 decimals)
- **Automated scheduling**: ETL runs every hour via APScheduler
- **Audit trail**: Raw data preserved for reprocessing
- **Async architecture**: High-performance async SQLAlchemy + asyncpg

---

## 🐳 Local Development Setup

### Prerequisites
- Docker Desktop installed and running
- Git (optional, for cloning)

### Quick Start

```bash
# Clone repository
git clone https://github.com/LikithsaiKovi/kasparro-backend-VenkataLikithSai-Kovi.git
cd kasparro-backend-VenkataLikithSai-Kovi

# Start all services (database + API)
docker-compose up --build
```

**Wait for these messages:**
```
✔ Container kasparro-backend-db-1   Created
✔ Container kasparro-backend-api-1  Created
api-1  | Database initialized successfully
api-1  | INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Test the API

**Open a new terminal and run:**

```bash
# Windows Command Prompt / PowerShell / Mac / Linux - all use same command
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "ok",
  "database": "connected",
  "timestamp": "2025-12-16T..."
}
```

### View Interactive Docs

Open in browser: http://localhost:8000/docs

### Stop Services

```bash
# Press Ctrl+C in the Docker terminal, then:
docker-compose down
```

---

## 🧪 Testing the System

### Test Checklist

**Production (Railway) - No Setup Required:**
- [ ] Test health: https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/health
- [ ] View data: https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/data?limit=5
- [ ] Check stats: https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/stats
- [ ] Browse docs: https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/docs

**Local (Docker):**
- [ ] Start: `docker-compose up --build`
- [ ] Test health: `curl http://localhost:8000/health`
- [ ] View data: `curl http://localhost:8000/data?limit=5`
- [ ] Check stats: `curl http://localhost:8000/stats`
- [ ] Browse docs: http://localhost:8000/docs

### Sample Test Queries

```bash
# Localhost
curl http://localhost:8000/data?ticker=BTC
curl http://localhost:8000/data?source=coinpaprika
curl http://localhost:8000/stats

# Production
curl https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/data?ticker=BTC
curl https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/data?source=coinpaprika
curl https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/stats
```

**For detailed testing instructions:** [API_TESTING.md](API_TESTING.md)

---

## 🗄️ Database Schema

**Tables:**
- `normalized_records` - Unified cryptocurrency data (one record per ticker)
- `raw_api_records` - Original API payloads (audit trail)
- `etl_checkpoints` - Incremental processing state
- `etl_runs` - ETL execution history

**Normalized Record Fields:**
- `id` - Unique identifier
- `ticker` - Symbol (uppercase, e.g., "BTC")
- `name` - Full name (e.g., "Bitcoin")
- `price_usd` - Current price (8 decimal precision)
- `market_cap_usd` - Market capitalization
- `volume_24h_usd` - 24-hour trading volume
- `percent_change_24h` - 24-hour price change
- `source` - Data source identifier
- `created_at` - Record creation timestamp
- `ingested_at` - ETL ingestion timestamp
  "name": "Kasparro Backend & ETL",
  "version": "1.1.2",
  "status": "running",
  "endpoints": {
    "health": "/health",
    "data": "/data",
    "stats": "/stats",
    "trigger_etl": "/trigger-etl",
    "docs": "/docs"
  }
}
```

**✅ Verification:** Should return API information with all available endpoints

---

---

## 🔧 Configuration

### Environment Variables

The system uses sensible defaults. Only `DATABASE_URL` is required:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes* | - | PostgreSQL connection string |
| `API_SOURCE_KEY` | No | `REPLACE_ME` | CoinPaprika API key (optional - free tier works without key) |
| `SCHEDULER_TOKEN` | No | - | Security token to protect ETL trigger endpoint |
| `LOG_LEVEL` | No | `INFO` | Logging level (INFO, DEBUG, WARNING, ERROR) |

*Automatically configured in Docker Compose and Railway

**For Docker Compose:** Environment is configured automatically, no `.env` file needed.

### SCHEDULER_TOKEN: Why & How

**Purpose**: Protects your ETL endpoint from unauthorized triggering

**Why It Matters**:
- **Cost Control**: ETL operations consume API quota and database resources
- **Security**: Prevents malicious actors from overloading your system with repeated ETL runs
- **Production Safety**: Ensures only authorized services (e.g., cron jobs, internal tools) can trigger data ingestion

**How It Works**:
1. Set `SCHEDULER_TOKEN=your_secret_token` in environment variables
2. To trigger ETL, include header: `X-Scheduler-Token: your_secret_token`
3. If token is set but missing/incorrect → `401 Unauthorized`
4. If token is not set → Endpoint is public (development only)

**Example (Postman)**:
```
POST /trigger-etl
Headers:
  X-Scheduler-Token: your_secret_token
```

**Best Practice**: Always set this in production deployments (Railway, AWS, etc.)

---

## 📁 Project Structure

```
kasparro-backend/
├── api/                    # FastAPI application
│   ├── main.py            # App initialization + ETL scheduler
│   ├── deps.py            # Dependency injection
│   └── routes/            # API endpoints
├── core/                  # Core configuration
│   ├── config.py          # Settings & validation
│   └── logger.py          # Logging setup
├── ingestion/             # ETL pipeline
│   ├── runner.py          # ETL orchestration
│   ├── transform.py       # Data transformation
│   ├── normalize.py       # Multi-source merging
│   └── sources/           # Data adapters
├── schemas/               # Pydantic models
├── services/              # Database layer
│   ├── db.py              # Connection management
│   └── models.py          # ORM models
├── tests/                 # Test suite
├── docker-compose.yml     # Local development
├── Dockerfile             # Multi-stage build
├── railway.json           # Railway IaC config
└── requirements.txt       # Dependencies
```

---

## 🚢 Deployment

### Railway (Production)

The app is deployed on Railway with automated CI/CD:

1. **Push to GitHub** → Railway auto-deploys
2. **Infrastructure as Code**: Configuration in `railway.json`
3. **Automatic DATABASE_URL**: Set by Railway PostgreSQL service
4. **ETL Automation**: Runs every hour automatically

**Deployment guide:** [RAILWAY_DEPLOYMENT.md](RAILWAY_DEPLOYMENT.md)

### Local Development

```bash
docker-compose up --build
```

That's it! Everything is configured automatically.

---

## 📚 Documentation

- **[TESTING_INSTRUCTIONS.md](TESTING_INSTRUCTIONS.md)** - Comprehensive testing guide
- **[TESTING_NORMALIZATION.md](TESTING_NORMALIZATION.md)** - Normalization testing
- **[NORMALIZATION.md](NORMALIZATION.md)** - Data normalization details

---

## 🐛 Troubleshooting

### Local Development

**Issue: "Connection refused"**
```bash
# Check if Docker is running
docker ps

# Check if services started
docker-compose ps
```

**Issue: "curl: command not found"**
```powershell
# Use PowerShell instead (Windows)
Invoke-WebRequest -Uri http://localhost:8000/health | Select-Object -ExpandProperty Content
```

### Production

**Issue: "database disconnected"**
- Ensure Railway PostgreSQL service is running and linked to your app
- Verify DATABASE_URL environment variable is set in Railway
- Check Railway logs: `railway logs`

---

## ✅ System Verification

**Verified Features:**
- ✅ Multi-source ETL (API + CSV ingestion)
- ✅ Automated scheduling (hourly runs)
- ✅ Data normalization (ticker unification)
- ✅ REST API with filtering & pagination
- ✅ Interactive documentation (Swagger UI)
- ✅ Docker containerization
- ✅ Production deployment on Railway
- ✅ Multi-stage Docker build (optimized)
- ✅ Infrastructure as Code

**Production Status:** ✅ Live on Railway  
**Last Updated:** December 2025  
**Version:** 1.1.2

---

## 👤 Author

Venkata Likith Sai Kovi

**Links:**
- 🌐 Live Demo: https://kasparro-backend-venkatalikithsai-kovi-production.up.railway.app/docs
- 💻 Repository: https://github.com/LikithsaiKovi/kasparro-backend-VenkataLikithSai-Kovi


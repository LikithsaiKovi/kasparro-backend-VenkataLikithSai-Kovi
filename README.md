# Kasparro Backend & ETL System

A production-ready ETL pipeline and REST API built with FastAPI, async SQLAlchemy, and PostgreSQL. The system ingests cryptocurrency data from multiple sources (CoinPaprika API, CoinGecko API, and CSV), stores raw data, performs schema normalization with ticker unification and price precision handling, and exposes queryable endpoints with comprehensive metadata and observability.

**Version:** 1.1.2

---

## 🚀 Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd kasparro-backend

# Create environment file
cp .env.example .env
# Edit .env and add your API_SOURCE_KEY (optional for demo)

# Start services (Postgres + API + ETL)
docker compose up --build

# API available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

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

---

## 📋 Features

### Core Functionality
- ✅ **Multi-source Data Ingestion**: CoinPaprika API, CoinGecko API, CSV files
- ✅ **ETL Pipeline**: Extract, Transform, Load with checkpointing
- ✅ **Data Normalization**: Unified schema with ticker normalization and price precision
- ✅ **REST API**: FastAPI with comprehensive endpoints
- ✅ **Database**: PostgreSQL with async SQLAlchemy
- ✅ **Raw Data Storage**: Preserves original payloads for audit trail
- ✅ **Observability**: Health checks, statistics, and ETL run tracking

### API Endpoints

- `GET /` - API information and available endpoints
- `GET /health` - Health check with database connectivity status
- `GET /data` - Query normalized records with filtering, pagination, and sorting
  - Query parameters: `source`, `ticker`, `start_date`, `end_date`, `limit`, `offset`
- `GET /stats` - ETL performance metrics and statistics
- `POST /trigger-etl` - Manually trigger an ETL run
- `GET /docs` - Interactive API documentation (Swagger UI)

---

## 🏗️ Architecture

```
External Sources → ETL Runner → PostgreSQL → FastAPI → API Clients
  (APIs, CSV)     (Transform)   (Raw +      (REST)
                              Normalized)
```

### Data Flow

1. **Extract**: Fetch data from CoinPaprika API, CoinGecko API, and CSV files
2. **Transform**: Normalize schemas, unify tickers, handle price precision
3. **Load**: Store in raw tables (audit) and normalized table (queryable)
4. **Query**: FastAPI endpoints expose normalized data with filtering

---

## 📁 Project Structure

```
kasparro-backend/
├── api/                    # FastAPI application
│   ├── main.py            # App initialization
│   ├── deps.py            # Dependency injection
│   └── routes/            # API endpoints
│       ├── data.py        # GET /data
│       ├── health.py      # GET /health
│       ├── stats.py       # GET /stats
│       └── trigger.py     # POST /trigger-etl
├── core/                  # Core configuration
│   ├── config.py          # Environment settings
│   └── logger.py          # Logging configuration
├── ingestion/             # ETL pipeline
│   ├── runner.py          # ETL orchestration
│   ├── transform.py       # Schema transformation
│   └── sources/           # Data source adapters
│       ├── api_source.py  # CoinPaprika/CoinGecko API
│       └── csv_source.py  # CSV file reader
├── schemas/               # Pydantic models
│   └── record.py          # Data validation schemas
├── services/              # Database layer
│   ├── db.py              # Database connection
│   └── models.py          # SQLAlchemy ORM models
├── tests/                 # Test suite
├── data/                  # Sample CSV files
├── docker-compose.yml     # Docker services
├── Dockerfile             # Container definition
├── requirements.txt       # Python dependencies
└── start.sh               # Container entrypoint
```

---

## 🗄️ Database Schema

### Tables

- **raw_api_records**: Original API payloads
- **raw_csv_records**: Original CSV records
- **normalized_records**: Unified, queryable schema
- **etl_checkpoints**: Incremental processing state
- **etl_runs**: ETL execution audit log

### Normalized Records Schema

- `id`: Primary key (source-specific identifier)
- `ticker`: Cryptocurrency ticker (normalized to uppercase)
- `name`: Full cryptocurrency name
- `price_usd`: Price in USD (normalized to 8 decimal places)
- `market_cap_usd`: Market capitalization
- `volume_24h_usd`: 24-hour trading volume
- `percent_change_24h`: 24-hour price change percentage
- `source`: Data source (coinpaprika, coingecko, csv)
- `created_at`: Source record creation time
- `ingested_at`: When record was saved

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL async connection string |
| `API_SOURCE_KEY` | No | `REPLACE_ME` | API authentication key (optional) |
| `CSV_PATH` | No | `data/sample.csv` | Path to CSV file |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `SCHEDULER_TOKEN` | No | - | Token for `/trigger-etl` authentication |

### Example `.env` File

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
API_SOURCE_KEY=
CSV_PATH=/data/sample.csv
LOG_LEVEL=INFO
SCHEDULER_TOKEN=
```

---

## 🧪 Testing

### Manual Testing

See [TESTING_INSTRUCTIONS.md](TESTING_INSTRUCTIONS.md) for detailed manual testing guide.

### Quick API Tests

```bash
# Health check
curl http://localhost:8000/health

# View data
curl http://localhost:8000/data?limit=5

# View statistics
curl http://localhost:8000/stats

# Trigger ETL
curl -X POST http://localhost:8000/trigger-etl
```

### Automated Tests

```bash
# Run tests
pytest -v

# With coverage
pytest --cov=. --cov-report=html
```

---

## 📊 API Examples

### Get All Data

```bash
GET /data?limit=10&offset=0
```

Response:
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
    "limit": 10,
    "offset": 0,
    "returned": 1,
    "total": 50
  },
  "meta": {
    "request_id": "req-1704892800000",
    "api_latency_ms": 12.45
  }
}
```

### Filter by Ticker

```bash
GET /data?ticker=BTC
```

### Filter by Source

```bash
GET /data?source=coinpaprika&limit=5
```

---

## 🔧 Development

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose (optional)

### Setup

1. Clone the repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `source venv/bin/activate` (Windows: `venv\Scripts\activate`)
4. Install dependencies: `pip install -r requirements.txt`
5. Set up environment variables (see Configuration section)
6. Initialize database: `python -m ingestion.runner --init-db`
7. Run ETL: `python -m ingestion.runner --once`
8. Start API: `uvicorn api.main:app --reload`

---

## 📝 Notes

- The system uses async SQLAlchemy with `asyncpg` for PostgreSQL connections
- Raw data is preserved for audit trail and reprocessing
- ETL uses checkpointing for incremental processing
- All timestamps are stored in UTC
- Ticker symbols are normalized to uppercase

---

## 📄 License

MIT License

---

## 👤 Author

Venkata Likith Sai Kovi

---

## 🔗 Links

- Interactive API Documentation: http://localhost:8000/docs
- Testing Instructions: [TESTING_INSTRUCTIONS.md](TESTING_INSTRUCTIONS.md)
- Normalization Details: [NORMALIZATION.md](NORMALIZATION.md)

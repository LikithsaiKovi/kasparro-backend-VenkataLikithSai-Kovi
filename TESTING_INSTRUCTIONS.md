# Manual Testing Instructions for Kasparro Backend

This guide will help you test the Kasparro backend manually using the Windows Command Prompt (cmd.exe).

## Prerequisites

1. **Python 3.11+** installed and accessible from command prompt
2. **PostgreSQL 15+** running locally, OR use Docker Compose
3. **pip** package manager

## Option 1: Using Docker Compose (Recommended - Easiest)

### Step 1: Set up Environment File

1. Open Command Prompt (cmd.exe)
2. Navigate to the project directory:
   ```
   cd C:\GitHub\kasparro-backend
   ```

3. Create a `.env` file from the example:
   ```
   copy .env.example .env
   ```

4. Edit `.env` file (using notepad or any text editor):
   ```
   notepad .env
   ```

   Set the following variables:
   ```
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/postgres
   API_SOURCE_KEY=REPLACE_ME
   LOG_LEVEL=INFO
   ```

### Step 2: Start Services with Docker Compose

```
docker-compose up --build
```

This will:
- Start PostgreSQL database
- Build and start the API service
- Automatically initialize the database
- Run ETL once in the background
- Start the FastAPI server on port 8000

Wait until you see: `Application startup complete` or `Uvicorn running on...`

### Step 3: Test the API Endpoints

Open a **NEW** Command Prompt window (keep the docker-compose one running) and test:

#### 3.1 Health Check
```cmd
curl http://localhost:8000/health
```

Expected: JSON response with `"status": "ok"` and database connection status

#### 3.2 View Data
```cmd
curl http://localhost:8000/data?limit=5
```

Expected: JSON response with cryptocurrency data array

#### 3.3 View Statistics
```cmd
curl http://localhost:8000/stats
```

Expected: JSON response with ETL statistics

#### 3.4 Trigger ETL Manually
```cmd
curl -X POST http://localhost:8000/trigger-etl
```

Expected: `{"status": "triggered", "timestamp": "..."}`

#### 3.5 Filter by Source
```cmd
curl "http://localhost:8000/data?source=api&limit=3"
```

#### 3.6 Filter by Ticker
```cmd
curl "http://localhost:8000/data?ticker=BTC"
```

### Step 4: View Interactive API Documentation

Open your web browser and navigate to:
```
http://localhost:8000/docs
```

This provides an interactive Swagger UI where you can test all endpoints directly.

### Step 5: Stop Services

When done testing, press `Ctrl+C` in the docker-compose window, then:
```cmd
docker-compose down
```

---

## Option 2: Local Development (Without Docker)

### Step 1: Set up Python Virtual Environment

```cmd
cd C:\GitHub\kasparro-backend

REM Create virtual environment
python -m venv venv

REM Activate virtual environment
venv\Scripts\activate.bat

REM Install dependencies
pip install -r requirements.txt
```

### Step 2: Set up PostgreSQL Database

**If you have PostgreSQL installed locally:**

1. Create a database:
   ```
   createdb kasparro_db
   ```

2. Set environment variables:
   ```cmd
   set DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/kasparro_db
   set API_SOURCE_KEY=REPLACE_ME
   set LOG_LEVEL=INFO
   ```

**Or use Docker just for the database:**
```cmd
docker run --name kasparro-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=postgres -p 5432:5432 -d postgres:15
```

Then set:
```cmd
set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/postgres
```

### Step 3: Initialize Database

```cmd
python -m ingestion.runner --init-db
```

Expected output: `Database initialized successfully`

### Step 4: Run ETL Once

```cmd
python -m ingestion.runner --once
```

This will:
- Fetch data from CoinPaprika API
- Store data in database

### Step 5: Start API Server

```cmd
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Wait for: `Uvicorn running on http://0.0.0.0:8000`

### Step 6: Test Endpoints

Open a **NEW** Command Prompt and run the same curl commands as in Option 1 (Step 3).

---

## Testing Checklist

Use this checklist to verify all functionality:

### API Endpoints
- [ ] `GET /health` - Returns status and database connection
- [ ] `GET /` - Returns API information
- [ ] `GET /data` - Returns paginated data
- [ ] `GET /data?limit=10` - Limits results to 10
- [ ] `GET /data?source=api` - Filters by source
- [ ] `GET /data?ticker=BTC` - Filters by ticker
- [ ] `GET /data?offset=5&limit=5` - Tests pagination
- [ ] `GET /stats` - Returns ETL statistics
- [ ] `POST /trigger-etl` - Triggers ETL run

### Data Verification
- [ ] Data appears in `/data` endpoint after ETL runs
- [ ] API data is present (source=coinpaprika)
- [ ] Tickers are normalized (uppercase)
- [ ] Prices are displayed correctly

### Error Handling
- [ ] Invalid endpoints return 404
- [ ] Health check works even if database is down (shows disconnected status)

---

## Common Issues and Solutions

### Issue: "ModuleNotFoundError"
**Solution:** Make sure virtual environment is activated and dependencies are installed:
```cmd
venv\Scripts\activate.bat
pip install -r requirements.txt
```

### Issue: "Connection refused" or "Database connection failed"
**Solution:** 
1. Verify PostgreSQL is running: `docker ps` (if using Docker)
2. Check DATABASE_URL environment variable is correct
3. Test connection: `psql -U postgres -h localhost` (or use pgAdmin)

### Issue: "Port 8000 already in use"
**Solution:** Use a different port:
```cmd
uvicorn api.main:app --port 8001
```
Then access: `http://localhost:8001`

### Issue: "curl is not recognized"
**Solution:** 
- Use PowerShell instead: `Invoke-WebRequest -Uri http://localhost:8000/health`
- Or install curl for Windows, or use the web browser to access `http://localhost:8000/docs`

---

## Using PowerShell Instead of CMD

If you prefer PowerShell, replace curl commands with:

```powershell
# Health check
Invoke-WebRequest -Uri http://localhost:8000/health | Select-Object -ExpandProperty Content

# Get data
Invoke-WebRequest -Uri "http://localhost:8000/data?limit=5" | Select-Object -ExpandProperty Content

# Trigger ETL
Invoke-WebRequest -Uri http://localhost:8000/trigger-etl -Method POST | Select-Object -ExpandProperty Content
```

---

## Next Steps

1. Explore the interactive API docs at `http://localhost:8000/docs`
2. Check logs for any errors or warnings
3. Modify the CSV file in `data/sample.csv` and re-run ETL
4. Review the code structure in the `api/`, `ingestion/`, and `services/` directories

---

## Need Help?

- Check the main README.md for architecture details
- Review API documentation at `/docs` endpoint
- Check Docker logs: `docker-compose logs -f`
- Verify environment variables are set correctly

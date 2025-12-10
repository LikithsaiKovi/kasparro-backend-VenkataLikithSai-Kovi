# Kasparro Backend & ETL

Backend + ETL system using FastAPI, async SQLAlchemy, and Postgres. It ingests from an API and a CSV source, stores raw data, normalizes records, exposes `/data`, `/health`, `/stats`, and `/trigger-etl` endpoints, and ships with Docker + compose + Makefile for quick spin-up.

## Requirements
- Python 3.11+
- Docker & docker-compose
- Make (optional but recommended)

## Quickstart
```bash
cp .env.example .env
# add API_SOURCE_KEY and adjust CSV_PATH if needed
make up        # builds and starts Postgres + API + ETL
make logs      # follow logs
make test      # run pytest inside container
make down      # stop stack
```

API runs on `http://localhost:8000`. Interactive docs at `/docs`.

## Endpoints
- `GET /data`: pagination + filters (source, start_date, end_date), returns metadata.
- `GET /health`: DB reachability + last ETL run.
- `GET /stats`: ETL summary (last success/failure, totals).
- `POST /trigger-etl`: kicks off an ETL cycle (optionally protect with scheduler token header).

## ETL design
- Sources: mock API (`ingestion/sources/api_source.py`) and CSV (`ingestion/sources/csv_source.py`).
- Raw tables: `raw_api_records`, `raw_csv_records`.
- Normalized table: `normalized_records` built via Pydantic validation in `ingestion/transform.py`.
- Checkpoint table: `etl_checkpoints` tracks last_id per source.
- Run tracking: `etl_runs` tracks status, counts, and durations.
- Idempotency: Postgres upserts for raw + normalized writes.

## Testing
```bash
make test
```
Includes transform, API, and failure-path coverage.

## Docker image (Docker Hub)
```bash
docker build -t your_dockerhub_username/kasparro-etl:latest .
docker run --env-file .env -p 8000:8000 your_dockerhub_username/kasparro-etl:latest
docker tag your_dockerhub_username/kasparro-etl:latest your_dockerhub_username/kasparro-etl:v1
docker push your_dockerhub_username/kasparro-etl:v1
```
Add the pushed image link here for reviewers.

## Cloud Run + Scheduler (example)
```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/kasparro-etl:v1
gcloud run deploy kasparro-etl \
  --image gcr.io/YOUR_PROJECT/kasparro-etl:v1 \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars API_SOURCE_KEY=projects/YOUR_PROJECT/secrets/API_KEY/versions/1
```
Create a Cloud Scheduler job to `POST https://<cloud-run-url>/trigger-etl` with `X-Scheduler-Token` header to run on cron.

## Project layout
```
ingestion/         # ETL logic
api/               # FastAPI app + routes
core/              # config, logging
schemas/           # Pydantic models
services/          # DB + models
tests/             # pytest suites
Dockerfile, docker-compose.yml, Makefile, start.sh
```

## Smoke checklist
- `make up` starts DB + API + background ETL.
- `/health` shows `status: ok`.
- `/data` returns paginated rows.
- `/stats` reflects run counts.
- `make test` passes.


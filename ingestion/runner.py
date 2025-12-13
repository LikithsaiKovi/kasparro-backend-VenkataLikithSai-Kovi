import argparse
import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logger import configure_logging
from ingestion.sources.api_source import fetch_api_records
from ingestion.sources.csv_source import fetch_csv_records
from ingestion.transform import transform_api_record, transform_csv_record
from schemas.record import NormalizedRecord
from services import models
from services.db import get_session, init_db

logger = logging.getLogger(__name__)
configure_logging()
settings = get_settings()


async def _get_checkpoint(session: AsyncSession, source: str) -> models.ETLCheckpoint:
    result = await session.execute(
        select(models.ETLCheckpoint).where(models.ETLCheckpoint.source == source)
    )
    checkpoint = result.scalar_one_or_none()
    if not checkpoint:
        checkpoint = models.ETLCheckpoint(source=source)
        session.add(checkpoint)
        await session.flush()
    return checkpoint


async def _update_checkpoint(session: AsyncSession, source: str, last_id: Optional[str]) -> None:
    checkpoint = await _get_checkpoint(session, source)
    checkpoint.last_id = last_id
    checkpoint.last_timestamp = datetime.utcnow()
    await session.flush()


async def _record_run(
    session: AsyncSession,
    source: str,
    status: str,
    processed: int = 0,
    failed: int = 0,
    message: Optional[str] = None,
    started_at: Optional[datetime] = None,
) -> models.ETLRun:
    run = models.ETLRun(
        source=source,
        status=status,
        started_at=started_at or datetime.utcnow(),
        finished_at=datetime.utcnow() if status != "running" else None,
        processed=processed,
        failed=failed,
        message=message,
    )
    session.add(run)
    await session.flush()
    return run


async def _finalize_run(session: AsyncSession, run: models.ETLRun, status: str, processed: int, failed: int, message: Optional[str] = None) -> None:
    run.status = status
    run.processed = processed
    run.failed = failed
    run.finished_at = datetime.utcnow()
    if run.started_at:
        run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)
    run.message = message
    await session.flush()


async def _upsert_normalized(session: AsyncSession, record: NormalizedRecord) -> None:
    """
    Upsert normalized record. Uses ticker to ensure one record per coin across all sources.
    This implements true normalization by coin name - all sources for the same ticker merge into one record.
    """
    from sqlalchemy import delete
    
    # First, delete any old-format records with the same ticker (e.g., coinpaprika_BTC, coingecko_BTC)
    # This ensures we don't have duplicate records from the migration period
    await session.execute(
        delete(models.NormalizedRecord)
        .where(models.NormalizedRecord.ticker == record.ticker)
        .where(
            (models.NormalizedRecord.id.like('coinpaprika_%')) |
            (models.NormalizedRecord.id.like('coingecko_%')) |
            (models.NormalizedRecord.id.like('csv_%'))
        )
    )
    
    # Check if a record with this ticker already exists (regardless of ID format)
    existing = await session.execute(
        select(models.NormalizedRecord).where(models.NormalizedRecord.ticker == record.ticker)
    )
    existing_record = existing.scalar_one_or_none()
    
    if existing_record:
        # Update existing record - this unifies all sources by ticker
        existing_record.id = record.id  # Update to new format
        existing_record.name = record.name
        existing_record.price_usd = record.price_usd
        existing_record.market_cap_usd = record.market_cap_usd
        existing_record.volume_24h_usd = record.volume_24h_usd
        existing_record.percent_change_24h = record.percent_change_24h
        existing_record.source = record.source
        existing_record.created_at = record.created_at
        existing_record.ingested_at = record.ingested_at or datetime.utcnow()
    else:
        # Insert new record
        new_record = models.NormalizedRecord(
            id=record.id,
            ticker=record.ticker,
            name=record.name,
            price_usd=record.price_usd,
            market_cap_usd=record.market_cap_usd,
            volume_24h_usd=record.volume_24h_usd,
            percent_change_24h=record.percent_change_24h,
            source=record.source,
            created_at=record.created_at,
            ingested_at=record.ingested_at or datetime.utcnow(),
        )
        session.add(new_record)
    
    await session.flush()


async def _ingest_api(session: AsyncSession) -> None:
    checkpoint = await _get_checkpoint(session, "api")
    last_id = checkpoint.last_id
    run = await _record_run(session, "api", status="running")

    try:
        raw_payloads = await fetch_api_records(settings.api_source_key, last_id=last_id)
        processed = failed = 0
        latest_seen = last_id

        for payload in raw_payloads:
            try:
                stmt = pg_insert(models.RawAPIRecord).values(
                    external_id=payload["external_id"],
                    payload=payload,
                ).on_conflict_do_nothing(index_elements=[models.RawAPIRecord.external_id])
                await session.execute(stmt)

                normalized = transform_api_record(payload)
                await _upsert_normalized(session, normalized)
                processed += 1
                latest_seen = max(latest_seen or normalized.id, normalized.id)
            except Exception as exc:  # noqa: BLE001
                logger.exception("API record failed validation/insert")
                failed += 1

        await _update_checkpoint(session, "api", latest_seen)
        await _finalize_run(session, run, status="success", processed=processed, failed=failed)
    except Exception as exc:  # noqa: BLE001
        await _finalize_run(session, run, status="failure", processed=0, failed=1, message=str(exc))
        raise


async def _ingest_csv(session: AsyncSession) -> None:
    checkpoint = await _get_checkpoint(session, "csv")
    last_id = checkpoint.last_id
    run = await _record_run(session, "csv", status="running")

    try:
        raw_payloads = fetch_csv_records(settings.csv_path, last_id=last_id)
        processed = failed = 0
        latest_seen = last_id

        for payload in raw_payloads:
            try:
                stmt = pg_insert(models.RawCSVRecord).values(
                    external_id=payload["external_id"],
                    payload=payload,
                ).on_conflict_do_nothing(index_elements=[models.RawCSVRecord.external_id])
                await session.execute(stmt)

                normalized = transform_csv_record(payload)
                await _upsert_normalized(session, normalized)
                processed += 1
                latest_seen = max(latest_seen or normalized.id, normalized.id)
            except Exception:
                logger.exception("CSV record failed validation/insert")
                failed += 1

        await _update_checkpoint(session, "csv", latest_seen)
        await _finalize_run(session, run, status="success", processed=processed, failed=failed)
    except Exception as exc:  # noqa: BLE001
        await _finalize_run(session, run, status="failure", processed=0, failed=1, message=str(exc))
        raise


async def run_once() -> None:
    async for session in get_session():
        await init_db()
        await _ingest_api(session)
        await _ingest_csv(session)
        await session.commit()


async def main(run_forever: bool = False) -> None:
    while True:
        async for session in get_session():
            await init_db()
            try:
                await _ingest_api(session)
                await _ingest_csv(session)
                await session.commit()
            except Exception:
                await session.rollback()
            finally:
                await session.close()
        if not run_forever:
            break
        await asyncio.sleep(300)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ETL runner")
    parser.add_argument("--once", action="store_true", help="Run ETL one time and exit")
    parser.add_argument("--init-db", action="store_true", help="Initialize tables")
    parser.add_argument("--run-forever", action="store_true", help="Keep running on an interval")
    args = parser.parse_args()

    if args.init_db:
        try:
            asyncio.run(init_db())
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            import sys
            sys.exit(1)

    if args.run_forever:
        asyncio.run(main(run_forever=True))
    elif args.once:
        try:
            asyncio.run(run_once())
        except Exception as e:
            logger.error(f"ETL run failed: {e}")
            import sys
            sys.exit(1)


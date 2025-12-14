import argparse
import asyncio
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.logger import configure_logging
from ingestion.sources.api_source import fetch_api_records
from ingestion.sources.csv_source import fetch_csv_records
from ingestion.transform import transform_api_record, transform_csv_record
from ingestion.normalize import merge_records
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
    Upsert normalized record using best-practice merging strategy.
    
    Merge Strategy:
    - Find existing record by ticker (if any)
    - Merge intelligently: most recent for volatile fields, canonical source for static fields
    - Preserve one record per ticker with enriched data from all sources
    """
    from sqlalchemy import select, delete
    
    # Find existing record by ticker (not by ID, since IDs differ per source)
    result = await session.execute(
        select(models.NormalizedRecord).where(models.NormalizedRecord.ticker == record.ticker)
    )
    existing_db_record = result.scalar_one_or_none()
    
    # Convert existing DB record to Pydantic model if exists
    existing_record = None
    if existing_db_record:
        existing_record = NormalizedRecord(
            id=existing_db_record.id,
            ticker=existing_db_record.ticker,
            name=existing_db_record.name,
            price_usd=existing_db_record.price_usd,
            market_cap_usd=existing_db_record.market_cap_usd,
            volume_24h_usd=existing_db_record.volume_24h_usd,
            percent_change_24h=existing_db_record.percent_change_24h,
            source=existing_db_record.source,
            created_at=existing_db_record.created_at,
            ingested_at=existing_db_record.ingested_at,
        )
    
    # Merge records using intelligent strategy
    merged_record = merge_records(existing_record, record)
    
    # Delete existing record if it exists (we'll insert merged version)
    if existing_db_record:
        await session.delete(existing_db_record)
        await session.flush()
    
    # Insert/Update with merged record
    # Use canonical ID format: merged_{ticker} to ensure one record per ticker
    merged_id = f"merged_{merged_record.ticker.lower()}"
    
    new_record = models.NormalizedRecord(
        id=merged_id,
        ticker=merged_record.ticker,
        name=merged_record.name,
        price_usd=merged_record.price_usd,
        market_cap_usd=merged_record.market_cap_usd,
        volume_24h_usd=merged_record.volume_24h_usd,
        percent_change_24h=merged_record.percent_change_24h,
        source=merged_record.source,  # Primary source after merge
        created_at=merged_record.created_at,
        ingested_at=merged_record.ingested_at or datetime.utcnow(),
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
                    payload=str(payload),  # Store as string
                ).on_conflict_do_nothing(index_elements=["external_id"])
                await session.execute(stmt)

                normalized = transform_api_record(payload)
                await _upsert_normalized(session, normalized)
                processed += 1
                latest_seen = max(latest_seen or normalized.id, normalized.id)
            except Exception as exc:
                logger.exception("API record failed validation/insert")
                failed += 1

        await _update_checkpoint(session, "api", latest_seen)
        await _finalize_run(session, run, status="success", processed=processed, failed=failed)
    except Exception as exc:
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
                    payload=str(payload),  # Store as string
                ).on_conflict_do_nothing(index_elements=["external_id"])
                await session.execute(stmt)

                normalized = transform_csv_record(payload)
                await _upsert_normalized(session, normalized)
                processed += 1
                latest_seen = max(latest_seen or normalized.id, normalized.id)
            except Exception as exc:
                logger.exception("CSV record failed validation/insert")
                failed += 1

        await _update_checkpoint(session, "csv", latest_seen)
        await _finalize_run(session, run, status="success", processed=processed, failed=failed)
    except Exception as exc:
        await _finalize_run(session, run, status="failure", processed=0, failed=1, message=str(exc))
        raise


async def run_once() -> None:
    async for session in get_session():
        await init_db()
        try:
            await _ingest_api(session)
            await _ingest_csv(session)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


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

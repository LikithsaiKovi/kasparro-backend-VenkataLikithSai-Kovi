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
from ingestion.transform import transform_api_record
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
    Upsert normalized record using best-practice merging strategy with improved concurrency safety.
    
    Merge Strategy:
    - Find existing record by ticker (if any) using FOR UPDATE lock for safety
    - Merge intelligently: most recent for volatile fields, canonical source for static fields
    - Preserve one record per ticker with enriched data from all sources
    
    Concurrency Safety:
    - Uses database-level locking (FOR UPDATE) to prevent race conditions
    - Transaction-scoped: All operations happen atomically within the session
    - Canonical ID ensures idempotent updates even with concurrent requests
    - For production systems with high concurrency, consider moving merge logic to a database trigger
    """
    from sqlalchemy import select, delete
    
    # Find existing record by ticker using FOR UPDATE lock for safe concurrent access
    # This prevents other transactions from modifying the same record while we're updating it
    result = await session.execute(
        select(models.NormalizedRecord)
        .where(models.NormalizedRecord.ticker == record.ticker)
        .with_for_update()  # Row-level lock: prevents other transactions from modifying this record
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
    
    # Use canonical ID format: merged_{ticker} to ensure one record per ticker
    # This ID is deterministic - same ticker always gets same ID
    merged_id = f"merged_{merged_record.ticker.lower()}"
    
    # Delete existing record if it exists (we're replacing it with the merged version)
    # This happens within the transaction, and the FOR UPDATE lock ensures no conflicts
    if existing_db_record:
        await session.delete(existing_db_record)
        await session.flush()
    
    # Insert merged record
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
    
    # NOTE: For even higher concurrency safety in a distributed system:
    # 1. Consider implementing a database trigger that performs the merge logic
    # 2. Or use PostgreSQL's ON CONFLICT clause with a custom conflict resolution function
    # 3. Example: INSERT INTO ... ON CONFLICT (ticker) DO UPDATE SET ...
    # The current approach is safe for typical single-server deployments and handles
    # concurrent requests within a single database instance correctly.


async def _ingest_api(session: AsyncSession) -> None:
    checkpoint = await _get_checkpoint(session, "coinpaprika")
    last_id = checkpoint.last_id
    run = await _record_run(session, "coinpaprika", status="running")

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

        await _update_checkpoint(session, "coinpaprika", latest_seen)
        await _finalize_run(session, run, status="success", processed=processed, failed=failed)
    except Exception as exc:
        await _finalize_run(session, run, status="failure", processed=0, failed=1, message=str(exc))
        raise


async def run_once() -> None:
    async for session in get_session():
        await init_db()
        try:
            await _ingest_api(session)
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

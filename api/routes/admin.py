from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from api.deps import get_db
from core.config import get_settings

router = APIRouter()


@router.post("/cleanup-csv")
async def cleanup_csv_data(
    x_scheduler_token: str | None = Header(default=None, alias="X-Scheduler-Token"),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove all legacy CSV-derived data so only real API data remains.

    - Deletes normalized records with source = 'csv'
    - Deletes ETL runs and checkpoints for source = 'csv'
    - Attempts to delete raw_csv_records table data if it exists
    """
    settings = get_settings()

    # Protect this endpoint behind the same scheduler token
    if settings.scheduler_token:
        if not x_scheduler_token or x_scheduler_token != settings.scheduler_token:
            raise HTTPException(status_code=401, detail="Invalid scheduler token")

    deleted = {"normalized": 0, "etl_runs": 0, "etl_checkpoints": 0, "raw_csv_records": 0}

    # Delete from normalized_records where source = 'csv'
    result = await db.execute(text("DELETE FROM normalized_records WHERE source = 'csv'"))
    deleted["normalized"] = result.rowcount or 0

    # Delete ETL runs and checkpoints for csv
    result = await db.execute(text("DELETE FROM etl_runs WHERE source = 'csv'"))
    deleted["etl_runs"] = result.rowcount or 0
    result = await db.execute(text("DELETE FROM etl_checkpoints WHERE source = 'csv'"))
    deleted["etl_checkpoints"] = result.rowcount or 0

    # Best-effort delete of raw_csv_records if table exists
    try:
        result = await db.execute(text("DELETE FROM raw_csv_records"))
        deleted["raw_csv_records"] = result.rowcount or 0
    except Exception:
        # Table might not exist anymore; ignore
        pass

    await db.commit()

    return {
        "status": "ok",
        "deleted": deleted,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db
from services import models

router = APIRouter()


@router.get("")
async def stats(db: AsyncSession = Depends(get_db)):
    total_records = await db.execute(select(func.count(models.NormalizedRecord.id)))
    total = total_records.scalar_one() or 0

    last_success = await db.execute(
        select(models.ETLRun).where(models.ETLRun.status == "success").order_by(models.ETLRun.finished_at.desc()).limit(1)
    )
    last_failure = await db.execute(
        select(models.ETLRun).where(models.ETLRun.status == "failure").order_by(models.ETLRun.finished_at.desc()).limit(1)
    )

    success_run = last_success.scalar_one_or_none()
    failure_run = last_failure.scalar_one_or_none()

    return {
        "total_normalized": total,
        "last_success": {
            "source": success_run.source if success_run else None,
            "finished_at": success_run.finished_at if success_run else None,
            "duration_ms": success_run.duration_ms if success_run else None,
            "processed": success_run.processed if success_run else None,
        },
        "last_failure": {
            "source": failure_run.source if failure_run else None,
            "finished_at": failure_run.finished_at if failure_run else None,
            "message": failure_run.message if failure_run else None,
        },
    }



from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db
from services import models

router = APIRouter()


@router.get("")
async def healthcheck(db: AsyncSession = Depends(get_db)):
    # connectivity check
    await db.execute(select(func.count(models.NormalizedRecord.id)))

    last_run = await db.execute(
        select(models.ETLRun).order_by(models.ETLRun.finished_at.desc()).limit(1)
    )
    run = last_run.scalar_one_or_none()
    return {
        "status": "ok",
        "database": "reachable",
        "last_etl": run.finished_at if run else None,
        "last_etl_status": run.status if run else None,
        "timestamp": datetime.utcnow(),
    }






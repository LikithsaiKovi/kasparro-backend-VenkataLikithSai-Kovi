from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db
from services import models

router = APIRouter()


@router.get("")
async def healthcheck(db: AsyncSession = Depends(get_db)):
    """Health check endpoint - checks database connectivity and last ETL run status."""
    try:
        # Try to check database connectivity
        await db.execute(select(func.count(models.NormalizedRecord.id)))
        db_status = "connected"
        
        last_run = await db.execute(
            select(models.ETLRun).order_by(models.ETLRun.finished_at.desc()).limit(1)
        )
        run = last_run.scalar_one_or_none()
        
        return {
            "status": "ok",
            "database": db_status,
            "last_etl": run.finished_at.isoformat() if run and run.finished_at else None,
            "last_etl_status": run.status if run else None,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        # Database not connected, but API is running
        return {
            "status": "ok",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
            "message": "API is running but database connection failed"
        }






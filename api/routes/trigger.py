from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db
from core.config import get_settings
from ingestion.runner import run_once

router = APIRouter()


@router.post("")
async def trigger_etl(
    background_tasks: BackgroundTasks,
    x_scheduler_token: str | None = Header(default=None, alias="X-Scheduler-Token"),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    
    # If SCHEDULER_TOKEN is set, require authentication
    if settings.scheduler_token:
        if not x_scheduler_token or x_scheduler_token != settings.scheduler_token:
            raise HTTPException(status_code=401, detail="Invalid scheduler token")

    background_tasks.add_task(run_once)
    return {"status": "triggered", "timestamp": datetime.utcnow().isoformat() + "Z"}






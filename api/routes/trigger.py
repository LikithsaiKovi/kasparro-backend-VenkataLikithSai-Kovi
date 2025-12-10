from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db
from ingestion.runner import run_once

router = APIRouter()


@router.post("")
async def trigger_etl(
    background_tasks: BackgroundTasks,
    x_scheduler_token: str | None = Header(default=None, convert_underscores=False),
    expected_token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if expected_token and x_scheduler_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid scheduler token")

    background_tasks.add_task(run_once)
    return {"status": "scheduled"}


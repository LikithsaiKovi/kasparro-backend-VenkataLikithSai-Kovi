import time
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from api.deps import get_db
from schemas.record import NormalizedRecord as NormalizedSchema
from services import models

router = APIRouter()


@router.get("", response_model=dict)
async def list_data(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source: Optional[str] = Query(None, description="Filter by source (e.g., coinpaprika)"),
    ticker: Optional[str] = Query(None, description="Filter by cryptocurrency ticker (e.g., BTC, ETH)"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    started = time.perf_counter()
    query = select(models.NormalizedRecord)

    if source:
        query = query.where(models.NormalizedRecord.source == source)
    if ticker:
        query = query.where(models.NormalizedRecord.ticker == ticker.upper())
    if start_date:
        query = query.where(models.NormalizedRecord.created_at >= start_date)
    if end_date:
        query = query.where(models.NormalizedRecord.created_at <= end_date)

    result = await db.execute(query)
    total_rows = result.scalars().all()
    items = total_rows[offset : offset + limit]
    records = [NormalizedSchema.model_validate(row, from_attributes=True).model_dump() for row in items]
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    return {
        "data": records,
        "pagination": {"limit": limit, "offset": offset, "returned": len(records), "total": len(total_rows)},
        "meta": {"request_id": f"req-{int(time.time()*1000)}", "api_latency_ms": latency_ms},
    }


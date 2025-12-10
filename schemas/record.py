from datetime import datetime
from pydantic import BaseModel, Field


class RawAPIItem(BaseModel):
    id: str = Field(..., alias="external_id")
    title: str
    value: float
    created_at: datetime

    class Config:
        populate_by_name = True


class RawCSVItem(BaseModel):
    id: str = Field(..., alias="external_id")
    description: str
    amount: float
    created_at: datetime

    class Config:
        populate_by_name = True


class NormalizedRecord(BaseModel):
    id: str
    title: str
    source: str
    value: float
    created_at: datetime


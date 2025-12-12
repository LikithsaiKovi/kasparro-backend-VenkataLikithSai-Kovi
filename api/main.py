from fastapi import FastAPI
from api.routes import data, health, stats, trigger
from core.logger import configure_logging

configure_logging()
app = FastAPI(title="Kasparro Backend & ETL")

app.include_router(data.router, prefix="/data", tags=["data"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
app.include_router(trigger.router, prefix="/trigger-etl", tags=["etl"])






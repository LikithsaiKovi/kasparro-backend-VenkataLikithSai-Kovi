import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from api.routes import data, health, stats, trigger, admin
from core.logger import configure_logging
from core.config import get_settings

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize scheduler
scheduler = AsyncIOScheduler()


async def run_scheduled_etl():
    """Run ETL process on schedule."""
    logger.info("Running scheduled ETL process...")
    try:
        from ingestion.runner import run_once
        await run_once()
        logger.info("Scheduled ETL process completed successfully")
    except Exception as e:
        logger.error(f"Scheduled ETL process failed: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown events."""
    # Startup
    logger.info("Starting Kasparro ETL Backend...")
    
    # Run initial ETL on startup
    logger.info("Running initial ETL process...")
    try:
        from ingestion.runner import run_once
        await run_once()
        logger.info("Initial ETL process completed successfully")
    except Exception as e:
        logger.error(f"Initial ETL process failed: {e}", exc_info=True)
    
    # Schedule ETL to run every hour
    scheduler.add_job(
        run_scheduled_etl,
        trigger=IntervalTrigger(hours=1),
        id='etl_job',
        name='Run ETL every hour',
        replace_existing=True
    )
    scheduler.start()
    logger.info("ETL scheduler started - will run every hour")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Kasparro ETL Backend...")
    scheduler.shutdown()
    logger.info("ETL scheduler stopped")


app = FastAPI(
    title="Kasparro Backend & ETL",
    description="Cryptocurrency ETL Pipeline with CoinPaprika and CoinGecko APIs",
    version="1.1.2",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Root endpoint - returns API information and available endpoints."""
    return {
        "name": "Kasparro Backend & ETL",
        "version": "1.1.2",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "data": "/data",
            "stats": "/stats",
            "trigger_etl": "/trigger-etl",
            "docs": "/docs",
            "openapi": "/openapi.json"
        },
        "description": "Cryptocurrency ETL Pipeline ingesting data from CoinPaprika, CoinGecko, and CSV sources",
        "etl_schedule": "Every hour (automated)"
    }

app.include_router(data.router, prefix="/data", tags=["data"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
app.include_router(trigger.router, prefix="/trigger-etl", tags=["etl"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])






import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from core.config import get_settings
from services import models

logger = logging.getLogger(__name__)
settings = get_settings()

# Log database URL (with password masked) for debugging
masked_url = settings.database_url
if '@' in masked_url:
    # Mask password in logs
    parts = masked_url.split('@')
    if '://' in parts[0]:
        protocol_user = parts[0].split('://')
        if ':' in protocol_user[1]:
            user = protocol_user[1].split(':')[0]
            masked_url = f"{protocol_user[0]}://{user}:****@{parts[1]}"
logger.info(f"Connecting to database: {masked_url}")

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

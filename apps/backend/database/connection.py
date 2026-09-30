import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import structlog

logger = structlog.get_logger()

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, "data", "ibvap_dev.db").replace("\\", "/")
DEFAULT_DB_URL = f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}"

# By default use local sqlite database if no URL is provided.
# The `+aiosqlite` adapter is required for async SQLite in SQLAlchemy 2.0.
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False, "timeout": 30.0} if "sqlite" in DATABASE_URL else {}
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection for FastAPI routers."""
    async with AsyncSessionLocal() as session:
        yield session

async def init_db() -> None:
    """Create all tables. Safe to call multiple times."""
    from . import models  # Ensures all ORM models are registered in Base.metadata
    from sqlalchemy import text
    async with engine.begin() as conn:
        if "sqlite" in DATABASE_URL:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA busy_timeout=30000;"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")

async def check_db_health() -> dict:
    """Check database connection latency."""
    import time
    from sqlalchemy import text
    start = time.time()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        return {"status": "ok", "latency_ms": round(latency, 2)}
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return {"status": "error", "error": str(e)}

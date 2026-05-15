"""
Database engine, session factory, and connection lifecycle management.

Uses asyncpg for async connections with connection pooling.
Graceful shutdown ensures all connections are returned to the pool.
"""

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from contextlib import asynccontextmanager
from app.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.async_database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,           # Verify connections before use
    pool_recycle=3600,            # Recycle connections after 1 hour
    connect_args={
        "server_settings": {
            "statement_timeout": "30000",  # 30s query timeout
            "lock_timeout": "5000",        # 5s lock wait timeout
        }
    },
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """FastAPI dependency that yields a database session and returns it."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def lifespan():
    """Application lifecycle: create tables on startup, dispose engine on shutdown."""
    logger.info("Initialising database engine and tables…")
    async with engine.begin() as conn:
        from app.models import all_models  # noqa: F401 (side-effect import)
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("Disposing database engine…")
    await engine.dispose()


async def init_db():
    """Create PostGIS extension and tables if they don't exist."""
    async with engine.begin() as conn:
        # Enable PostGIS if available (required for Geography columns)
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        except Exception as e:
            logger.warning(f"PostGIS extension not available: {e}")
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except Exception as e:
            logger.warning(f"pgvector extension not available: {e}")
        from app.models import all_models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    await engine.dispose()
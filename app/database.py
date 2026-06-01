import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.config import settings

logger = logging.getLogger(__name__)

# Core Async Engine setup using asyncpg
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,             # Persistent pool size
    max_overflow=10,          # Allow up to 10 additional connections under load
    pool_pre_ping=True,       # Pre-validate connections before checking out
    pool_recycle=3600,        # Recycle connections after 1 hour
    echo=False,
)

# Async Session Factory
# expire_on_commit=False is crucial for async execution to prevent DetachedInstanceError
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# FastAPI Dependency Injection
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Asynchronous dependency yield generator for SQLAlchemy DB sessions.
    Automatically handles commits, rollbacks on exception, and session closing.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Database transaction error: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()

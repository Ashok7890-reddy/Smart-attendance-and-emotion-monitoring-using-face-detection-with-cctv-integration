"""
Database connection management.
"""

import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData
import redis.asyncio as redis
from contextlib import asynccontextmanager


class Base(DeclarativeBase):
    """Base class for all database models."""
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s"
        }
    )


class DatabaseManager:
    """Database connection manager."""
    
    def __init__(self):
        self.postgres_engine = None
        self.async_session_maker = None
        self.redis_client = None
    
    async def initialize(self):
        """Initialize database connections."""
        # PostgreSQL connection
        postgres_url = os.getenv(
            "DATABASE_URL", 
            "postgresql+asyncpg://postgres:password@localhost:5432/smart_attendance"
        )
        
        self.postgres_engine = create_async_engine(
            postgres_url,
            echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        self.async_session_maker = async_sessionmaker(
            self.postgres_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Redis connection
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20
        )
    
    async def close(self):
        """Close database connections."""
        if self.postgres_engine:
            await self.postgres_engine.dispose()
        if self.redis_client:
            await self.redis_client.close()
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session context manager."""
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def get_redis(self) -> redis.Redis:
        """Get Redis client."""
        return self.redis_client


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with db_manager.get_session() as session:
        yield session


async def get_redis_client() -> redis.Redis:
    """Dependency for getting Redis client."""
    return await db_manager.get_redis()
"""
Database management utilities.
"""

import asyncio
import os
from typing import List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from alembic.config import Config
from alembic import command
import logging

from .connection import db_manager, Base
from .schemas import (
    StudentSchema, AttendanceSessionSchema, AttendanceRecordSchema,
    FaceDetectionSchema, EmotionResultSchema, EmotionStatisticsSchema,
    SystemHealthSchema, AuditLogSchema
)

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database management operations."""
    
    def __init__(self):
        self.alembic_cfg = None
        self._setup_alembic()
    
    def _setup_alembic(self):
        """Setup Alembic configuration."""
        migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
        alembic_ini_path = os.path.join(migrations_dir, "alembic.ini")
        
        if os.path.exists(alembic_ini_path):
            self.alembic_cfg = Config(alembic_ini_path)
            self.alembic_cfg.set_main_option("script_location", migrations_dir)
    
    async def create_database(self, database_url: Optional[str] = None):
        """Create database if it doesn't exist."""
        if not database_url:
            database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            raise ValueError("Database URL not provided")
        
        # Extract database name from URL
        db_name = database_url.split("/")[-1]
        server_url = database_url.rsplit("/", 1)[0] + "/postgres"
        
        try:
            from sqlalchemy.ext.asyncio import create_async_engine
            engine = create_async_engine(server_url, isolation_level="AUTOCOMMIT")
            
            async with engine.connect() as conn:
                # Check if database exists
                result = await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": db_name}
                )
                
                if not result.fetchone():
                    await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                    logger.info(f"Created database: {db_name}")
                else:
                    logger.info(f"Database already exists: {db_name}")
            
            await engine.dispose()
            
        except Exception as e:
            logger.error(f"Error creating database: {e}")
            raise
    
    async def drop_database(self, database_url: Optional[str] = None):
        """Drop database (use with caution!)."""
        if not database_url:
            database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            raise ValueError("Database URL not provided")
        
        # Extract database name from URL
        db_name = database_url.split("/")[-1]
        server_url = database_url.rsplit("/", 1)[0] + "/postgres"
        
        try:
            from sqlalchemy.ext.asyncio import create_async_engine
            engine = create_async_engine(server_url, isolation_level="AUTOCOMMIT")
            
            async with engine.connect() as conn:
                # Terminate existing connections
                await conn.execute(
                    text("""
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = :db_name AND pid <> pg_backend_pid()
                    """),
                    {"db_name": db_name}
                )
                
                # Drop database
                await conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
                logger.info(f"Dropped database: {db_name}")
            
            await engine.dispose()
            
        except Exception as e:
            logger.error(f"Error dropping database: {e}")
            raise
    
    def run_migrations(self):
        """Run database migrations."""
        if not self.alembic_cfg:
            raise RuntimeError("Alembic configuration not found")
        
        try:
            command.upgrade(self.alembic_cfg, "head")
            logger.info("Database migrations completed successfully")
        except Exception as e:
            logger.error(f"Error running migrations: {e}")
            raise
    
    def create_migration(self, message: str):
        """Create a new migration."""
        if not self.alembic_cfg:
            raise RuntimeError("Alembic configuration not found")
        
        try:
            command.revision(self.alembic_cfg, message=message, autogenerate=True)
            logger.info(f"Created migration: {message}")
        except Exception as e:
            logger.error(f"Error creating migration: {e}")
            raise
    
    def downgrade_migration(self, revision: str = "-1"):
        """Downgrade to a specific migration."""
        if not self.alembic_cfg:
            raise RuntimeError("Alembic configuration not found")
        
        try:
            command.downgrade(self.alembic_cfg, revision)
            logger.info(f"Downgraded to revision: {revision}")
        except Exception as e:
            logger.error(f"Error downgrading migration: {e}")
            raise
    
    async def reset_database(self):
        """Reset database by dropping and recreating all tables."""
        try:
            await db_manager.initialize()
            
            async with db_manager.postgres_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database reset completed")
            
        except Exception as e:
            logger.error(f"Error resetting database: {e}")
            raise
        finally:
            await db_manager.close()
    
    async def check_connection(self) -> bool:
        """Check database connection health."""
        try:
            await db_manager.initialize()
            
            async with db_manager.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.fetchone() is not None
                
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
        finally:
            await db_manager.close()
    
    async def get_table_counts(self) -> dict:
        """Get row counts for all tables."""
        try:
            await db_manager.initialize()
            counts = {}
            
            async with db_manager.get_session() as session:
                tables = [
                    ("students", StudentSchema),
                    ("attendance_sessions", AttendanceSessionSchema),
                    ("attendance_records", AttendanceRecordSchema),
                    ("face_detections", FaceDetectionSchema),
                    ("emotion_results", EmotionResultSchema),
                    ("emotion_statistics", EmotionStatisticsSchema),
                    ("system_health", SystemHealthSchema),
                    ("audit_logs", AuditLogSchema),
                ]
                
                for table_name, schema_class in tables:
                    result = await session.execute(
                        text(f"SELECT COUNT(*) FROM {table_name}")
                    )
                    counts[table_name] = result.scalar()
            
            return counts
            
        except Exception as e:
            logger.error(f"Error getting table counts: {e}")
            return {}
        finally:
            await db_manager.close()


# Global database manager instance
database_manager = DatabaseManager()


async def init_database():
    """Initialize database with tables and initial data."""
    try:
        # Create database if it doesn't exist
        await database_manager.create_database()
        
        # Initialize database manager
        await db_manager.initialize()
        
        # Run migrations
        database_manager.run_migrations()
        
        logger.info("Database initialization completed successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        await db_manager.close()


if __name__ == "__main__":
    # CLI interface for database management
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m backend.database.manager <command>")
        print("Commands: init, reset, check, counts, create-migration, migrate")
        sys.exit(1)
    
    command_name = sys.argv[1]
    
    async def run_command():
        if command_name == "init":
            await init_database()
        elif command_name == "reset":
            await database_manager.reset_database()
        elif command_name == "check":
            is_healthy = await database_manager.check_connection()
            print(f"Database connection: {'OK' if is_healthy else 'FAILED'}")
        elif command_name == "counts":
            counts = await database_manager.get_table_counts()
            for table, count in counts.items():
                print(f"{table}: {count}")
        elif command_name == "create-migration":
            if len(sys.argv) < 3:
                print("Usage: python -m backend.database.manager create-migration <message>")
                sys.exit(1)
            message = " ".join(sys.argv[2:])
            database_manager.create_migration(message)
        elif command_name == "migrate":
            database_manager.run_migrations()
        else:
            print(f"Unknown command: {command_name}")
            sys.exit(1)
    
    asyncio.run(run_command())
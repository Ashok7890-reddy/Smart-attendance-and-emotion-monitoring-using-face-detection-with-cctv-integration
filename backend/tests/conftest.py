"""
Test configuration and fixtures.
"""

import pytest
import asyncio
import os
import tempfile
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import redis.asyncio as redis
import numpy as np

from backend.database.connection import Base
from backend.database.schemas import (
    StudentSchema, AttendanceSessionSchema, AttendanceRecordSchema,
    FaceDetectionSchema, EmotionResultSchema, EmotionStatisticsSchema
)
from backend.core.encryption import EncryptionManager, FaceEmbeddingStorage
from backend.core.cache import CacheManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db_engine():
    """Create test database engine."""
    # Use in-memory SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session_maker = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session


@pytest.fixture
def test_encryption_key():
    """Test encryption key."""
    return "test_encryption_key_for_unit_tests_only"


@pytest.fixture
def encryption_manager(test_encryption_key):
    """Create encryption manager for testing."""
    return EncryptionManager(test_encryption_key)


@pytest.fixture
def face_embedding_storage(encryption_manager):
    """Create face embedding storage for testing."""
    return FaceEmbeddingStorage(encryption_manager)


@pytest.fixture
async def test_redis_client():
    """Create test Redis client (mock)."""
    # Use fakeredis for testing
    try:
        import fakeredis.aioredis
        client = fakeredis.aioredis.FakeRedis()
        yield client
        await client.close()
    except ImportError:
        # If fakeredis not available, skip Redis tests
        pytest.skip("fakeredis not available for testing")


@pytest.fixture
async def cache_manager(test_redis_client):
    """Create cache manager for testing."""
    return CacheManager(test_redis_client)


@pytest.fixture
def sample_face_embedding():
    """Create sample face embedding for testing."""
    np.random.seed(42)  # For reproducible tests
    return np.random.rand(512).astype(np.float32)


@pytest.fixture
def sample_student_data():
    """Sample student data for testing."""
    from backend.models.student import StudentType
    from datetime import datetime
    
    return {
        "student_id": "STU001",
        "name": "John Doe",
        "student_type": StudentType.DAY_SCHOLAR,
        "enrollment_date": datetime(2024, 1, 15),
        "is_active": True,
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "class_id": "CS101"
    }


@pytest.fixture
def sample_session_data():
    """Sample attendance session data for testing."""
    from datetime import datetime
    
    return {
        "session_id": "SES001",
        "class_id": "CS101",
        "faculty_id": "FAC001",
        "start_time": datetime(2024, 11, 3, 10, 0, 0),
        "total_registered": 30,
        "total_detected": 0,
        "is_active": True
    }


@pytest.fixture
def sample_attendance_record():
    """Sample attendance record for testing."""
    from backend.models.attendance import AttendanceStatus
    from datetime import datetime
    
    return {
        "student_id": "STU001",
        "session_id": "SES001",
        "status": AttendanceStatus.PRESENT,
        "timestamp": datetime(2024, 11, 3, 10, 5, 0),
        "confidence": 0.95,
        "classroom_entry_time": datetime(2024, 11, 3, 10, 5, 0)
    }


@pytest.fixture
def sample_face_detection():
    """Sample face detection for testing."""
    from backend.models.face_detection import CameraLocation
    from datetime import datetime
    import numpy as np
    
    return {
        "bounding_box": (100, 100, 200, 200),
        "confidence": 0.92,
        "embedding": np.random.rand(512).astype(np.float32),
        "liveness_score": 0.88,
        "timestamp": datetime(2024, 11, 3, 10, 5, 0),
        "camera_location": CameraLocation.CLASSROOM,
        "student_id": "STU001"
    }


@pytest.fixture
def sample_emotion_result():
    """Sample emotion result for testing."""
    from backend.models.emotion import EmotionType
    from datetime import datetime
    
    return {
        "student_id": "STU001",
        "emotion": EmotionType.INTERESTED,
        "confidence": 0.85,
        "timestamp": datetime(2024, 11, 3, 10, 5, 0),
        "engagement_score": 0.8
    }
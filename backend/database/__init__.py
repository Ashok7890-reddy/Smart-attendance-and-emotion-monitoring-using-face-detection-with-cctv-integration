"""
Database package for Smart Attendance System.
"""

from .connection import (
    Base,
    DatabaseManager,
    db_manager,
    get_db_session,
    get_redis_client
)
from .schemas import (
    StudentSchema,
    AttendanceSessionSchema,
    AttendanceRecordSchema,
    FaceDetectionSchema,
    EmotionResultSchema,
    EmotionStatisticsSchema,
    SystemHealthSchema,
    AuditLogSchema
)
from .manager import database_manager, init_database

__all__ = [
    # Connection management
    "Base",
    "DatabaseManager", 
    "db_manager",
    "get_db_session",
    "get_redis_client",
    
    # Database schemas
    "StudentSchema",
    "AttendanceSessionSchema", 
    "AttendanceRecordSchema",
    "FaceDetectionSchema",
    "EmotionResultSchema",
    "EmotionStatisticsSchema",
    "SystemHealthSchema",
    "AuditLogSchema",
    
    # Database manager
    "database_manager",
    "init_database"
]
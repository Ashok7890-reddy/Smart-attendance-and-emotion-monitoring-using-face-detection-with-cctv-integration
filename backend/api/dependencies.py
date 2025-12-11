"""
FastAPI dependencies for dependency injection.
"""

from functools import lru_cache
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from datetime import datetime

from ..core.config import Config
from ..database.manager import DatabaseManager
from ..database.repositories import (
    StudentRepository, 
    AttendanceRepository, 
    FaceDetectionRepository
)
from ..services.attendance_service import AttendanceService
from ..services.face_recognition_service import FaceRecognitionService
from ..services.validation_service import ValidationService
from ..services.notification_service import NotificationService

# Security
security = HTTPBearer()


@lru_cache()
def get_config() -> Config:
    """Get application configuration."""
    return Config()


@lru_cache()
def get_database_manager() -> DatabaseManager:
    """Get database manager instance."""
    return DatabaseManager()


async def get_student_repository(
    db_manager: Annotated[DatabaseManager, Depends(get_database_manager)]
) -> StudentRepository:
    """Get student repository."""
    return StudentRepository(db_manager)


async def get_attendance_repository(
    db_manager: Annotated[DatabaseManager, Depends(get_database_manager)]
) -> AttendanceRepository:
    """Get attendance repository."""
    return AttendanceRepository(db_manager)


async def get_face_detection_repository(
    db_manager: Annotated[DatabaseManager, Depends(get_database_manager)]
) -> FaceDetectionRepository:
    """Get face detection repository."""
    return FaceDetectionRepository(db_manager)


async def get_face_recognition_service() -> FaceRecognitionService:
    """Get face recognition service."""
    config = get_config()
    return FaceRecognitionService(config.face_recognition)


async def get_attendance_service(
    attendance_repo: Annotated[AttendanceRepository, Depends(get_attendance_repository)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    face_detection_repo: Annotated[FaceDetectionRepository, Depends(get_face_detection_repository)],
    face_recognition_service: Annotated[FaceRecognitionService, Depends(get_face_recognition_service)]
) -> AttendanceService:
    """Get attendance service."""
    return AttendanceService(
        attendance_repo=attendance_repo,
        student_repo=student_repo,
        face_detection_repo=face_detection_repo,
        face_recognition_service=face_recognition_service
    )


async def get_validation_service(
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
) -> ValidationService:
    """Get validation service."""
    return ValidationService(attendance_service)


async def get_notification_service() -> NotificationService:
    """Get notification service."""
    config = get_config()
    return NotificationService(config)


async def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    config: Annotated[Config, Depends(get_config)]
) -> dict:
    """Verify JWT token and return user info."""
    try:
        token = credentials.credentials
        payload = jwt.decode(
            token, 
            config.security.jwt_secret, 
            algorithms=["HS256"]
        )
        
        # Check token expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow().timestamp() > exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        
        return payload
        
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user(
    token_data: Annotated[dict, Depends(verify_token)]
) -> dict:
    """Get current authenticated user."""
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    return {
        "user_id": user_id,
        "role": token_data.get("role", "user"),
        "permissions": token_data.get("permissions", [])
    }


async def require_faculty_role(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Require faculty role for access."""
    if current_user.get("role") not in ["faculty", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faculty access required"
        )
    return current_user


async def require_admin_role(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Require admin role for access."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from ..models.student import StudentType
from ..models.attendance import AttendanceStatus


class StudentTypeEnum(str, Enum):
    """Student type enumeration for API."""
    DAY_SCHOLAR = "day_scholar"
    HOSTEL_STUDENT = "hostel_student"


class AttendanceStatusEnum(str, Enum):
    """Attendance status enumeration for API."""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    INCOMPLETE = "incomplete"


# Authentication Schemas
class LoginRequest(BaseModel):
    """Login request schema."""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class LoginResponse(BaseModel):
    """Login response schema."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_info: Dict[str, Any]


# Student Schemas
class StudentCreate(BaseModel):
    """Schema for creating a new student."""
    student_id: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    student_type: StudentTypeEnum
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    class_id: Optional[str] = Field(None, max_length=20)


class StudentUpdate(BaseModel):
    """Schema for updating student information."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    student_type: Optional[StudentTypeEnum] = None
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    class_id: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None


class StudentResponse(BaseModel):
    """Schema for student response."""
    student_id: str
    name: str
    student_type: StudentTypeEnum
    enrollment_date: datetime
    is_active: bool
    email: Optional[str] = None
    phone: Optional[str] = None
    class_id: Optional[str] = None


class FaceRegistrationRequest(BaseModel):
    """Schema for face registration request."""
    student_id: str
    image_data: str = Field(..., description="Base64 encoded image data")


# Session Schemas
class SessionCreate(BaseModel):
    """Schema for creating attendance session."""
    class_id: str = Field(..., min_length=1, max_length=20)
    faculty_id: str = Field(..., min_length=1, max_length=20)


class SessionResponse(BaseModel):
    """Schema for session response."""
    session_id: str
    class_id: str
    faculty_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_registered: int
    total_detected: int
    is_active: bool


class SessionUpdate(BaseModel):
    """Schema for updating session."""
    end_time: Optional[datetime] = None
    is_active: Optional[bool] = None


# Attendance Schemas
class AttendanceRecordResponse(BaseModel):
    """Schema for attendance record response."""
    student_id: str
    session_id: str
    status: AttendanceStatusEnum
    timestamp: datetime
    confidence: float
    gate_entry_time: Optional[datetime] = None
    classroom_entry_time: Optional[datetime] = None


class GateEntryRequest(BaseModel):
    """Schema for gate entry request."""
    student_id: str
    timestamp: Optional[datetime] = None
    
    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        return v or datetime.utcnow()


class ClassroomAttendanceRequest(BaseModel):
    """Schema for classroom attendance request."""
    session_id: str
    detections: List[Dict[str, Any]] = Field(..., description="List of face detection data")


class AttendanceReportRequest(BaseModel):
    """Schema for attendance report request."""
    session_id: str
    include_emotions: bool = Field(default=True)
    include_cross_verification: bool = Field(default=True)


class AttendanceReportResponse(BaseModel):
    """Schema for attendance report response."""
    session_info: Dict[str, Any]
    overall_statistics: Dict[str, Any]
    day_scholar_report: Dict[str, Any]
    hostel_student_report: Dict[str, Any]
    alerts: List[str]
    generated_at: datetime


class RealTimeAttendanceResponse(BaseModel):
    """Schema for real-time attendance response."""
    session_id: str
    class_id: str
    total_registered: int
    total_present: int
    total_absent: int
    attendance_percentage: float
    present_students: List[Dict[str, Any]]
    absent_students: List[Dict[str, Any]]
    session_start: datetime
    is_active: bool


# Validation Schemas
class ValidationRequest(BaseModel):
    """Schema for attendance validation request."""
    session_id: str


class ValidationResponse(BaseModel):
    """Schema for validation response."""
    session_id: str
    validation_status: str
    total_registered: int
    total_detected: int
    missing_students: List[Dict[str, Any]]
    alerts: List[str]
    validation_timestamp: datetime


class CrossVerificationResponse(BaseModel):
    """Schema for cross-verification response."""
    session_id: str
    total_day_scholars: int
    verified_count: int
    incomplete_count: int
    verification_rate: float
    missing_gate_entry: List[Dict[str, Any]]
    timing_violations: List[Dict[str, Any]]
    alerts: List[str]


# System Health Schemas
class SystemHealthResponse(BaseModel):
    """Schema for system health response."""
    status: str
    timestamp: datetime
    services: Dict[str, Dict[str, Any]]
    cameras: Dict[str, Dict[str, Any]]
    database: Dict[str, Any]
    redis: Dict[str, Any]


# Error Schemas
class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationErrorResponse(BaseModel):
    """Schema for validation error responses."""
    detail: str
    errors: List[Dict[str, Any]]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Bulk Operations Schemas
class BulkStudentCreate(BaseModel):
    """Schema for bulk student creation."""
    students: List[StudentCreate] = Field(..., min_items=1, max_items=100)


class BulkOperationResponse(BaseModel):
    """Schema for bulk operation response."""
    total_items: int
    successful_items: int
    failed_items: int
    errors: List[Dict[str, Any]]
    results: List[Dict[str, Any]]


# Statistics Schemas
class AttendanceStatistics(BaseModel):
    """Schema for attendance statistics."""
    date_range: Dict[str, datetime]
    total_sessions: int
    average_attendance_rate: float
    day_scholar_stats: Dict[str, Any]
    hostel_student_stats: Dict[str, Any]
    class_wise_stats: List[Dict[str, Any]]


class EmotionStatistics(BaseModel):
    """Schema for emotion statistics."""
    session_id: str
    total_detections: int
    emotion_breakdown: Dict[str, float]
    engagement_score: float
    timestamp_stats: List[Dict[str, Any]]


# WebSocket Schemas
class WebSocketMessage(BaseModel):
    """Schema for WebSocket messages."""
    type: str = Field(..., description="Message type")
    data: Dict[str, Any] = Field(..., description="Message data")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AttendanceUpdateMessage(WebSocketMessage):
    """Schema for attendance update WebSocket messages."""
    type: str = "attendance_update"
    session_id: str
    student_count: int
    attendance_percentage: float


class EmotionUpdateMessage(WebSocketMessage):
    """Schema for emotion update WebSocket messages."""
    type: str = "emotion_update"
    session_id: str
    emotion_stats: Dict[str, float]
    engagement_score: float


class AlertMessage(WebSocketMessage):
    """Schema for alert WebSocket messages."""
    type: str = "alert"
    severity: str
    message: str
    session_id: Optional[str] = None


# Face Recognition Schemas
class FaceRecognitionRequest(BaseModel):
    """Schema for face recognition request."""
    image_data: str = Field(..., description="Base64 encoded image data")


class FaceRecognitionResponse(BaseModel):
    """Schema for face recognition response."""
    student_id: str
    name: str
    student_type: str
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recognition confidence score")
    bounding_box: List[int] = Field(..., description="Face bounding box [x1, y1, x2, y2]")
    liveness_score: float = Field(..., ge=0.0, le=1.0, description="Liveness detection score")
    emotion: Optional[str] = Field(None, description="Detected emotion")


class MultipleFaceRecognitionResponse(BaseModel):
    """Schema for multiple face recognition response."""
    detections: List[FaceRecognitionResponse]
    total_faces: int = Field(..., description="Total number of faces detected in image")

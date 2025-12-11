"""
Database schema definitions using SQLAlchemy.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Float, 
    Text, LargeBinary, ForeignKey, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from .connection import Base
from ..models.student import StudentType
from ..models.attendance import AttendanceStatus
from ..models.emotion import EmotionType
from ..models.face_detection import CameraLocation


class StudentSchema(Base):
    """Student database schema."""
    __tablename__ = "students"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    student_type = Column(SQLEnum(StudentType), nullable=False, index=True)
    face_embedding = Column(LargeBinary, nullable=False)  # Encrypted embedding
    enrollment_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    class_id = Column(String(50), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    attendance_records = relationship("AttendanceRecordSchema", back_populates="student")
    emotion_results = relationship("EmotionResultSchema", back_populates="student")
    
    # Indexes
    __table_args__ = (
        Index("ix_students_type_active", "student_type", "is_active"),
        Index("ix_students_class_active", "class_id", "is_active"),
    )


class AttendanceSessionSchema(Base):
    """Attendance session database schema."""
    __tablename__ = "attendance_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), unique=True, nullable=False, index=True)
    class_id = Column(String(50), nullable=False, index=True)
    faculty_id = Column(String(50), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    total_registered = Column(Integer, default=0, nullable=False)
    total_detected = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    attendance_records = relationship("AttendanceRecordSchema", back_populates="session")
    emotion_statistics = relationship("EmotionStatisticsSchema", back_populates="session")
    
    # Indexes
    __table_args__ = (
        Index("ix_sessions_class_date", "class_id", "start_time"),
        Index("ix_sessions_faculty_date", "faculty_id", "start_time"),
    )


class AttendanceRecordSchema(Base):
    """Attendance record database schema."""
    __tablename__ = "attendance_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(String(50), ForeignKey("students.student_id"), nullable=False, index=True)
    session_id = Column(String(100), ForeignKey("attendance_sessions.session_id"), nullable=False, index=True)
    status = Column(SQLEnum(AttendanceStatus), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    confidence = Column(Float, nullable=False)
    gate_entry_time = Column(DateTime, nullable=True)
    classroom_entry_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    student = relationship("StudentSchema", back_populates="attendance_records")
    session = relationship("AttendanceSessionSchema", back_populates="attendance_records")
    
    # Indexes
    __table_args__ = (
        Index("ix_attendance_student_session", "student_id", "session_id"),
        Index("ix_attendance_session_status", "session_id", "status"),
        Index("ix_attendance_timestamp", "timestamp"),
    )


class FaceDetectionSchema(Base):
    """Face detection database schema."""
    __tablename__ = "face_detections"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bounding_box = Column(JSONB, nullable=False)  # Store as JSON: [x, y, width, height]
    confidence = Column(Float, nullable=False, index=True)
    embedding = Column(LargeBinary, nullable=False)  # Numpy array as bytes
    liveness_score = Column(Float, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    camera_location = Column(SQLEnum(CameraLocation), nullable=False, index=True)
    student_id = Column(String(50), ForeignKey("students.student_id"), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    student = relationship("StudentSchema")
    
    # Indexes
    __table_args__ = (
        Index("ix_detections_camera_time", "camera_location", "timestamp"),
        Index("ix_detections_student_time", "student_id", "timestamp"),
        Index("ix_detections_confidence", "confidence"),
        Index("ix_detections_liveness", "liveness_score"),
    )


class EmotionResultSchema(Base):
    """Emotion result database schema."""
    __tablename__ = "emotion_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(String(50), ForeignKey("students.student_id"), nullable=False, index=True)
    session_id = Column(String(100), ForeignKey("attendance_sessions.session_id"), nullable=False, index=True)
    emotion = Column(SQLEnum(EmotionType), nullable=False, index=True)
    confidence = Column(Float, nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    engagement_score = Column(Float, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    student = relationship("StudentSchema", back_populates="emotion_results")
    
    # Indexes
    __table_args__ = (
        Index("ix_emotions_student_session", "student_id", "session_id"),
        Index("ix_emotions_session_time", "session_id", "timestamp"),
        Index("ix_emotions_type_confidence", "emotion", "confidence"),
    )


class EmotionStatisticsSchema(Base):
    """Emotion statistics database schema."""
    __tablename__ = "emotion_statistics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(100), ForeignKey("attendance_sessions.session_id"), nullable=False, index=True)
    total_frames = Column(Integer, nullable=False)
    emotion_counts = Column(JSONB, nullable=False)  # Store emotion counts as JSON
    emotion_percentages = Column(JSONB, nullable=False)  # Store percentages as JSON
    average_engagement_score = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    session = relationship("AttendanceSessionSchema", back_populates="emotion_statistics")


class SystemHealthSchema(Base):
    """System health monitoring schema."""
    __tablename__ = "system_health"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    component = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)  # healthy, warning, error
    message = Column(Text, nullable=True)
    metrics = Column(JSONB, nullable=True)  # Store performance metrics
    timestamp = Column(DateTime, nullable=False, index=True)
    
    # Indexes
    __table_args__ = (
        Index("ix_health_component_time", "component", "timestamp"),
        Index("ix_health_status_time", "status", "timestamp"),
    )


class AuditLogSchema(Base):
    """Audit log for biometric data access."""
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(50), nullable=True, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Indexes
    __table_args__ = (
        Index("ix_audit_action_time", "action", "timestamp"),
        Index("ix_audit_resource_time", "resource_type", "timestamp"),
        Index("ix_audit_user_time", "user_id", "timestamp"),
    )
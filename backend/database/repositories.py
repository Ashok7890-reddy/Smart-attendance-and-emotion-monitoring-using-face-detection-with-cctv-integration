"""
Repository pattern implementations for database operations.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from datetime import timedelta
from sqlalchemy.orm import selectinload
import numpy as np
import logging

from .schemas import (
    StudentSchema, AttendanceSessionSchema, AttendanceRecordSchema,
    FaceDetectionSchema, EmotionResultSchema, EmotionStatisticsSchema,
    SystemHealthSchema, AuditLogSchema
)
from ..models.student import Student, StudentType, StudentMatch
from ..models.attendance import AttendanceRecord, AttendanceSession, AttendanceStatus
from ..models.face_detection import FaceDetection, CameraLocation
from ..models.emotion import EmotionResult, EmotionType, EmotionStatistics
from ..core.encryption import get_face_embedding_storage

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository with common operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.face_storage = get_face_embedding_storage()


class StudentRepository(BaseRepository):
    """Repository for student operations."""
    
    async def create_student(self, student: Student) -> StudentSchema:
        """Create a new student with encrypted face embedding."""
        try:
            # Encrypt face embedding
            storage_data = self.face_storage.store_embedding(
                student.student_id, 
                np.frombuffer(student.face_embedding, dtype=np.float32)
            )
            
            db_student = StudentSchema(
                student_id=student.student_id,
                name=student.name,
                student_type=student.student_type,
                face_embedding=storage_data['encrypted_embedding'],
                enrollment_date=student.enrollment_date,
                is_active=student.is_active,
                email=student.email,
                phone=student.phone,
                class_id=student.class_id
            )
            
            self.session.add(db_student)
            await self.session.flush()
            
            logger.info(f"Student created: {student.student_id}")
            return db_student
            
        except Exception as e:
            logger.error(f"Failed to create student {student.student_id}: {e}")
            raise
    
    async def get_student_by_id(self, student_id: str) -> Optional[StudentSchema]:
        """Get student by ID."""
        try:
            result = await self.session.execute(
                select(StudentSchema).where(StudentSchema.student_id == student_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get student {student_id}: {e}")
            return None
    
    async def get_students_by_class(self, class_id: str, active_only: bool = True) -> List[StudentSchema]:
        """Get all students in a class."""
        try:
            query = select(StudentSchema).where(StudentSchema.class_id == class_id)
            if active_only:
                query = query.where(StudentSchema.is_active == True)
            
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get students for class {class_id}: {e}")
            return []
    
    async def get_students_by_type(self, student_type: StudentType, active_only: bool = True) -> List[StudentSchema]:
        """Get students by type (day scholar or hostel)."""
        try:
            query = select(StudentSchema).where(StudentSchema.student_type == student_type)
            if active_only:
                query = query.where(StudentSchema.is_active == True)
            
            result = await self.session.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get students by type {student_type}: {e}")
            return []
    
    async def update_student(self, student_id: str, updates: Dict[str, Any]) -> bool:
        """Update student information."""
        try:
            # Handle face embedding update if provided
            if 'face_embedding' in updates:
                embedding = updates['face_embedding']
                if isinstance(embedding, np.ndarray):
                    storage_data = self.face_storage.store_embedding(student_id, embedding)
                    updates['face_embedding'] = storage_data['encrypted_embedding']
            
            updates['updated_at'] = datetime.utcnow()
            
            result = await self.session.execute(
                update(StudentSchema)
                .where(StudentSchema.student_id == student_id)
                .values(**updates)
            )
            
            success = result.rowcount > 0
            if success:
                logger.info(f"Student updated: {student_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update student {student_id}: {e}")
            return False
    
    async def deactivate_student(self, student_id: str) -> bool:
        """Deactivate a student."""
        return await self.update_student(student_id, {'is_active': False})
    
    async def get_student_embedding(self, student_id: str) -> Optional[np.ndarray]:
        """Get decrypted face embedding for a student."""
        try:
            student = await self.get_student_by_id(student_id)
            if not student or not student.face_embedding:
                return None
            
            embedding = self.face_storage.retrieve_embedding(student.face_embedding)
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to get embedding for student {student_id}: {e}")
            return None
    
    async def search_students(self, query: str, limit: int = 50) -> List[StudentSchema]:
        """Search students by name or ID."""
        try:
            search_query = select(StudentSchema).where(
                or_(
                    StudentSchema.name.ilike(f"%{query}%"),
                    StudentSchema.student_id.ilike(f"%{query}%")
                )
            ).limit(limit)
            
            result = await self.session.execute(search_query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Failed to search students with query '{query}': {e}")
            return []


class AttendanceRepository(BaseRepository):
    """Repository for attendance operations."""
    
    async def create_session(self, session: AttendanceSession) -> AttendanceSessionSchema:
        """Create a new attendance session."""
        try:
            db_session = AttendanceSessionSchema(
                session_id=session.session_id,
                class_id=session.class_id,
                faculty_id=session.faculty_id,
                start_time=session.start_time,
                end_time=session.end_time,
                total_registered=session.total_registered,
                total_detected=session.total_detected,
                is_active=session.is_active
            )
            
            self.session.add(db_session)
            await self.session.flush()
            
            logger.info(f"Attendance session created: {session.session_id}")
            return db_session
            
        except Exception as e:
            logger.error(f"Failed to create session {session.session_id}: {e}")
            raise
    
    async def get_session_by_id(self, session_id: str) -> Optional[AttendanceSessionSchema]:
        """Get attendance session by ID."""
        try:
            result = await self.session.execute(
                select(AttendanceSessionSchema)
                .options(selectinload(AttendanceSessionSchema.attendance_records))
                .where(AttendanceSessionSchema.session_id == session_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def get_active_sessions(self) -> List[AttendanceSessionSchema]:
        """Get all active attendance sessions."""
        try:
            result = await self.session.execute(
                select(AttendanceSessionSchema)
                .where(AttendanceSessionSchema.is_active == True)
                .order_by(AttendanceSessionSchema.start_time.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get active sessions")
            return []
    
    async def create_attendance_record(self, record: AttendanceRecord) -> AttendanceRecordSchema:
        """Create an attendance record."""
        try:
            db_record = AttendanceRecordSchema(
                student_id=record.student_id,
                session_id=record.session_id,
                status=record.status,
                timestamp=record.timestamp,
                confidence=record.confidence,
                gate_entry_time=record.gate_entry_time,
                classroom_entry_time=record.classroom_entry_time
            )
            
            self.session.add(db_record)
            await self.session.flush()
            
            logger.debug(f"Attendance record created: {record.student_id} - {record.status}")
            return db_record
            
        except Exception as e:
            logger.error(f"Failed to create attendance record: {e}")
            raise
    
    async def update_session_counts(self, session_id: str, total_detected: int) -> bool:
        """Update session detection counts."""
        try:
            result = await self.session.execute(
                update(AttendanceSessionSchema)
                .where(AttendanceSessionSchema.session_id == session_id)
                .values(
                    total_detected=total_detected,
                    updated_at=datetime.utcnow()
                )
            )
            
            return result.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to update session counts for {session_id}: {e}")
            return False
    
    async def end_session(self, session_id: str) -> bool:
        """End an attendance session."""
        try:
            result = await self.session.execute(
                update(AttendanceSessionSchema)
                .where(AttendanceSessionSchema.session_id == session_id)
                .values(
                    end_time=datetime.utcnow(),
                    is_active=False,
                    updated_at=datetime.utcnow()
                )
            )
            
            success = result.rowcount > 0
            if success:
                logger.info(f"Session ended: {session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return False
    
    async def get_session_attendance(self, session_id: str) -> List[AttendanceRecordSchema]:
        """Get all attendance records for a session."""
        try:
            result = await self.session.execute(
                select(AttendanceRecordSchema)
                .options(selectinload(AttendanceRecordSchema.student))
                .where(AttendanceRecordSchema.session_id == session_id)
                .order_by(AttendanceRecordSchema.timestamp)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get attendance for session {session_id}: {e}")
            return []
    
    async def get_student_attendance_history(self, student_id: str, limit: int = 50) -> List[AttendanceRecordSchema]:
        """Get attendance history for a student."""
        try:
            result = await self.session.execute(
                select(AttendanceRecordSchema)
                .options(selectinload(AttendanceRecordSchema.session))
                .where(AttendanceRecordSchema.student_id == student_id)
                .order_by(AttendanceRecordSchema.timestamp.desc())
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get attendance history for student {student_id}: {e}")
            return []
    
    async def update_attendance_record(self, record_id: str, updates: Dict[str, Any]) -> bool:
        """Update an attendance record."""
        try:
            updates['updated_at'] = datetime.utcnow()
            
            result = await self.session.execute(
                update(AttendanceRecordSchema)
                .where(AttendanceRecordSchema.id == record_id)
                .values(**updates)
            )
            
            success = result.rowcount > 0
            if success:
                logger.debug(f"Attendance record updated: {record_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update attendance record {record_id}: {e}")
            return False


class FaceDetectionRepository(BaseRepository):
    """Repository for face detection operations."""
    
    async def create_detection(self, detection: FaceDetection) -> FaceDetectionSchema:
        """Create a face detection record."""
        try:
            # Convert bounding box to JSON format
            bbox_json = {
                'x': detection.bounding_box[0],
                'y': detection.bounding_box[1], 
                'width': detection.bounding_box[2],
                'height': detection.bounding_box[3]
            }
            
            db_detection = FaceDetectionSchema(
                bounding_box=bbox_json,
                confidence=detection.confidence,
                embedding=detection.embedding.tobytes(),
                liveness_score=detection.liveness_score,
                timestamp=detection.timestamp,
                camera_location=detection.camera_location,
                student_id=detection.student_id
            )
            
            self.session.add(db_detection)
            await self.session.flush()
            
            logger.debug(f"Face detection created: {detection.camera_location} - {detection.confidence:.3f}")
            return db_detection
            
        except Exception as e:
            logger.error(f"Failed to create face detection: {e}")
            raise
    
    async def get_recent_detections(self, camera_location: CameraLocation, minutes: int = 10) -> List[FaceDetectionSchema]:
        """Get recent detections from a camera."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
            
            result = await self.session.execute(
                select(FaceDetectionSchema)
                .where(
                    and_(
                        FaceDetectionSchema.camera_location == camera_location,
                        FaceDetectionSchema.timestamp >= cutoff_time
                    )
                )
                .order_by(FaceDetectionSchema.timestamp.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get recent detections for {camera_location}: {e}")
            return []
    
    async def get_detections_by_session(self, session_id: str) -> List[FaceDetectionSchema]:
        """Get all detections for a session."""
        try:
            result = await self.session.execute(
                select(FaceDetectionSchema)
                .where(FaceDetectionSchema.session_id == session_id)
                .order_by(FaceDetectionSchema.timestamp)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get detections for session {session_id}: {e}")
            return []


class EmotionRepository(BaseRepository):
    """Repository for emotion analysis operations."""
    
    async def create_emotion_result(self, emotion: EmotionResult) -> EmotionResultSchema:
        """Create an emotion analysis result."""
        try:
            db_emotion = EmotionResultSchema(
                student_id=emotion.student_id,
                session_id=emotion.student_id,  # This should be session_id from context
                emotion=emotion.emotion,
                confidence=emotion.confidence,
                timestamp=emotion.timestamp,
                engagement_score=emotion.engagement_score
            )
            
            self.session.add(db_emotion)
            await self.session.flush()
            
            logger.debug(f"Emotion result created: {emotion.student_id} - {emotion.emotion}")
            return db_emotion
            
        except Exception as e:
            logger.error(f"Failed to create emotion result: {e}")
            raise
    
    async def create_emotion_statistics(self, stats: EmotionStatistics) -> EmotionStatisticsSchema:
        """Create emotion statistics for a session."""
        try:
            db_stats = EmotionStatisticsSchema(
                session_id=stats.session_id,
                total_frames=stats.total_frames,
                emotion_counts={emotion.value: count for emotion, count in stats.emotion_counts.items()},
                emotion_percentages={emotion.value: pct for emotion, pct in stats.emotion_percentages.items()},
                average_engagement_score=stats.average_engagement_score
            )
            
            self.session.add(db_stats)
            await self.session.flush()
            
            logger.info(f"Emotion statistics created for session: {stats.session_id}")
            return db_stats
            
        except Exception as e:
            logger.error(f"Failed to create emotion statistics: {e}")
            raise
    
    async def get_session_emotions(self, session_id: str) -> List[EmotionResultSchema]:
        """Get all emotion results for a session."""
        try:
            result = await self.session.execute(
                select(EmotionResultSchema)
                .where(EmotionResultSchema.session_id == session_id)
                .order_by(EmotionResultSchema.timestamp)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Failed to get emotions for session {session_id}: {e}")
            return []
    
    async def get_session_statistics(self, session_id: str) -> Optional[EmotionStatisticsSchema]:
        """Get emotion statistics for a session."""
        try:
            result = await self.session.execute(
                select(EmotionStatisticsSchema)
                .where(EmotionStatisticsSchema.session_id == session_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Failed to get emotion statistics for session {session_id}: {e}")
            return None


class AuditRepository(BaseRepository):
    """Repository for audit logging operations."""
    
    async def log_action(self, action: str, resource_type: str, resource_id: str, 
                        user_id: Optional[str] = None, success: bool = True, 
                        error_message: Optional[str] = None, 
                        ip_address: Optional[str] = None,
                        user_agent: Optional[str] = None) -> AuditLogSchema:
        """Log an audit action."""
        try:
            audit_log = AuditLogSchema(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                error_message=error_message
            )
            
            self.session.add(audit_log)
            await self.session.flush()
            
            logger.debug(f"Audit log created: {action} on {resource_type}:{resource_id}")
            return audit_log
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")
            raise
    
    async def get_audit_logs(self, resource_type: Optional[str] = None, 
                           user_id: Optional[str] = None, 
                           limit: int = 100) -> List[AuditLogSchema]:
        """Get audit logs with optional filtering."""
        try:
            query = select(AuditLogSchema)
            
            if resource_type:
                query = query.where(AuditLogSchema.resource_type == resource_type)
            if user_id:
                query = query.where(AuditLogSchema.user_id == user_id)
            
            query = query.order_by(AuditLogSchema.timestamp.desc()).limit(limit)
            
            result = await self.session.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error("Failed to get audit logs")
            return []
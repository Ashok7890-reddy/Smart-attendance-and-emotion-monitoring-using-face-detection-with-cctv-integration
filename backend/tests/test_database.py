"""
Unit tests for database operations and schemas.
"""

import pytest
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy import select

from backend.database.schemas import (
    StudentSchema, AttendanceSessionSchema, AttendanceRecordSchema,
    FaceDetectionSchema, EmotionResultSchema, EmotionStatisticsSchema
)
from backend.database.repositories import (
    StudentRepository, AttendanceRepository, FaceDetectionRepository, EmotionRepository
)
from backend.models.student import Student, StudentType
from backend.models.attendance import AttendanceRecord, AttendanceSession, AttendanceStatus
from backend.models.face_detection import FaceDetection, CameraLocation
from backend.models.emotion import EmotionResult, EmotionType, EmotionStatistics


class TestDatabaseSchemas:
    """Test database schema creation and basic operations."""
    
    async def test_student_schema_creation(self, test_db_session, sample_student_data, sample_face_embedding, face_embedding_storage):
        """Test creating student in database."""
        # Encrypt embedding
        storage_data = face_embedding_storage.store_embedding("STU001", sample_face_embedding)
        
        student = StudentSchema(
            **sample_student_data,
            face_embedding=storage_data["encrypted_embedding"]
        )
        
        test_db_session.add(student)
        await test_db_session.commit()
        
        # Verify student was created
        result = await test_db_session.execute(
            select(StudentSchema).where(StudentSchema.student_id == "STU001")
        )
        db_student = result.scalar_one()
        
        assert db_student.student_id == "STU001"
        assert db_student.name == "John Doe"
        assert db_student.student_type == StudentType.DAY_SCHOLAR
        assert db_student.is_active is True
        assert db_student.face_embedding is not None
    
    async def test_attendance_session_schema_creation(self, test_db_session, sample_session_data):
        """Test creating attendance session in database."""
        session = AttendanceSessionSchema(**sample_session_data)
        
        test_db_session.add(session)
        await test_db_session.commit()
        
        # Verify session was created
        result = await test_db_session.execute(
            select(AttendanceSessionSchema).where(AttendanceSessionSchema.session_id == "SES001")
        )
        db_session = result.scalar_one()
        
        assert db_session.session_id == "SES001"
        assert db_session.class_id == "CS101"
        assert db_session.faculty_id == "FAC001"
        assert db_session.is_active is True
    
    async def test_attendance_record_schema_creation(self, test_db_session, sample_student_data, sample_session_data, sample_attendance_record, sample_face_embedding, face_embedding_storage):
        """Test creating attendance record in database."""
        # Create student first
        storage_data = face_embedding_storage.store_embedding("STU001", sample_face_embedding)
        student = StudentSchema(**sample_student_data, face_embedding=storage_data["encrypted_embedding"])
        test_db_session.add(student)
        
        # Create session
        session = AttendanceSessionSchema(**sample_session_data)
        test_db_session.add(session)
        
        # Create attendance record
        record = AttendanceRecordSchema(**sample_attendance_record)
        test_db_session.add(record)
        
        await test_db_session.commit()
        
        # Verify record was created
        result = await test_db_session.execute(
            select(AttendanceRecordSchema).where(
                AttendanceRecordSchema.student_id == "STU001"
            )
        )
        db_record = result.scalar_one()
        
        assert db_record.student_id == "STU001"
        assert db_record.session_id == "SES001"
        assert db_record.status == AttendanceStatus.PRESENT
        assert db_record.confidence == 0.95
    
    async def test_face_detection_schema_creation(self, test_db_session, sample_student_data, sample_face_detection, sample_face_embedding, face_embedding_storage):
        """Test creating face detection in database."""
        # Create student first
        storage_data = face_embedding_storage.store_embedding("STU001", sample_face_embedding)
        student = StudentSchema(**sample_student_data, face_embedding=storage_data["encrypted_embedding"])
        test_db_session.add(student)
        
        # Create face detection
        bbox_json = {
            'x': sample_face_detection["bounding_box"][0],
            'y': sample_face_detection["bounding_box"][1],
            'width': sample_face_detection["bounding_box"][2],
            'height': sample_face_detection["bounding_box"][3]
        }
        
        detection = FaceDetectionSchema(
            bounding_box=bbox_json,
            confidence=sample_face_detection["confidence"],
            embedding=sample_face_detection["embedding"].tobytes(),
            liveness_score=sample_face_detection["liveness_score"],
            timestamp=sample_face_detection["timestamp"],
            camera_location=sample_face_detection["camera_location"],
            student_id=sample_face_detection["student_id"]
        )
        
        test_db_session.add(detection)
        await test_db_session.commit()
        
        # Verify detection was created
        result = await test_db_session.execute(
            select(FaceDetectionSchema).where(FaceDetectionSchema.student_id == "STU001")
        )
        db_detection = result.scalar_one()
        
        assert db_detection.student_id == "STU001"
        assert db_detection.confidence == 0.92
        assert db_detection.camera_location == CameraLocation.CLASSROOM
        assert db_detection.bounding_box["x"] == 100
    
    async def test_emotion_result_schema_creation(self, test_db_session, sample_student_data, sample_session_data, sample_emotion_result, sample_face_embedding, face_embedding_storage):
        """Test creating emotion result in database."""
        # Create student and session first
        storage_data = face_embedding_storage.store_embedding("STU001", sample_face_embedding)
        student = StudentSchema(**sample_student_data, face_embedding=storage_data["encrypted_embedding"])
        session = AttendanceSessionSchema(**sample_session_data)
        
        test_db_session.add(student)
        test_db_session.add(session)
        
        # Create emotion result
        emotion = EmotionResultSchema(
            student_id=sample_emotion_result["student_id"],
            session_id="SES001",  # Use session ID from fixture
            emotion=sample_emotion_result["emotion"],
            confidence=sample_emotion_result["confidence"],
            timestamp=sample_emotion_result["timestamp"],
            engagement_score=sample_emotion_result["engagement_score"]
        )
        
        test_db_session.add(emotion)
        await test_db_session.commit()
        
        # Verify emotion was created
        result = await test_db_session.execute(
            select(EmotionResultSchema).where(EmotionResultSchema.student_id == "STU001")
        )
        db_emotion = result.scalar_one()
        
        assert db_emotion.student_id == "STU001"
        assert db_emotion.emotion == EmotionType.INTERESTED
        assert db_emotion.confidence == 0.85
        assert db_emotion.engagement_score == 0.8


class TestStudentRepository:
    """Test StudentRepository operations."""
    
    async def test_create_student(self, test_db_session, sample_student_data, sample_face_embedding):
        """Test creating student through repository."""
        repo = StudentRepository(test_db_session)
        
        student = Student(
            **sample_student_data,
            face_embedding=sample_face_embedding.tobytes()
        )
        
        db_student = await repo.create_student(student)
        
        assert db_student.student_id == "STU001"
        assert db_student.name == "John Doe"
        assert db_student.face_embedding is not None
    
    async def test_get_student_by_id(self, test_db_session, sample_student_data, sample_face_embedding):
        """Test getting student by ID."""
        repo = StudentRepository(test_db_session)
        
        # Create student
        student = Student(
            **sample_student_data,
            face_embedding=sample_face_embedding.tobytes()
        )
        await repo.create_student(student)
        await test_db_session.commit()
        
        # Get student
        db_student = await repo.get_student_by_id("STU001")
        
        assert db_student is not None
        assert db_student.student_id == "STU001"
        assert db_student.name == "John Doe"
    
    async def test_get_student_embedding(self, test_db_session, sample_student_data, sample_face_embedding):
        """Test getting decrypted student embedding."""
        repo = StudentRepository(test_db_session)
        
        # Create student
        student = Student(
            **sample_student_data,
            face_embedding=sample_face_embedding.tobytes()
        )
        await repo.create_student(student)
        await test_db_session.commit()
        
        # Get embedding
        embedding = await repo.get_student_embedding("STU001")
        
        assert embedding is not None
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == sample_face_embedding.shape
        np.testing.assert_array_almost_equal(embedding, sample_face_embedding)
    
    async def test_get_students_by_class(self, test_db_session, sample_face_embedding):
        """Test getting students by class."""
        repo = StudentRepository(test_db_session)
        
        # Create multiple students
        students_data = [
            {
                "student_id": "STU001",
                "name": "John Doe",
                "student_type": StudentType.DAY_SCHOLAR,
                "enrollment_date": datetime.now(),
                "class_id": "CS101"
            },
            {
                "student_id": "STU002", 
                "name": "Jane Smith",
                "student_type": StudentType.HOSTEL_STUDENT,
                "enrollment_date": datetime.now(),
                "class_id": "CS101"
            },
            {
                "student_id": "STU003",
                "name": "Bob Johnson", 
                "student_type": StudentType.DAY_SCHOLAR,
                "enrollment_date": datetime.now(),
                "class_id": "CS102"
            }
        ]
        
        for student_data in students_data:
            student = Student(
                **student_data,
                face_embedding=sample_face_embedding.tobytes()
            )
            await repo.create_student(student)
        
        await test_db_session.commit()
        
        # Get students by class
        cs101_students = await repo.get_students_by_class("CS101")
        cs102_students = await repo.get_students_by_class("CS102")
        
        assert len(cs101_students) == 2
        assert len(cs102_students) == 1
        assert all(s.class_id == "CS101" for s in cs101_students)
    
    async def test_update_student(self, test_db_session, sample_student_data, sample_face_embedding):
        """Test updating student information."""
        repo = StudentRepository(test_db_session)
        
        # Create student
        student = Student(
            **sample_student_data,
            face_embedding=sample_face_embedding.tobytes()
        )
        await repo.create_student(student)
        await test_db_session.commit()
        
        # Update student
        updates = {
            "name": "John Updated Doe",
            "email": "john.updated@example.com",
            "phone": "+9876543210"
        }
        
        success = await repo.update_student("STU001", updates)
        await test_db_session.commit()
        
        assert success is True
        
        # Verify updates
        updated_student = await repo.get_student_by_id("STU001")
        assert updated_student.name == "John Updated Doe"
        assert updated_student.email == "john.updated@example.com"
        assert updated_student.phone == "+9876543210"
    
    async def test_deactivate_student(self, test_db_session, sample_student_data, sample_face_embedding):
        """Test deactivating student."""
        repo = StudentRepository(test_db_session)
        
        # Create student
        student = Student(
            **sample_student_data,
            face_embedding=sample_face_embedding.tobytes()
        )
        await repo.create_student(student)
        await test_db_session.commit()
        
        # Deactivate student
        success = await repo.deactivate_student("STU001")
        await test_db_session.commit()
        
        assert success is True
        
        # Verify deactivation
        deactivated_student = await repo.get_student_by_id("STU001")
        assert deactivated_student.is_active is False


class TestAttendanceRepository:
    """Test AttendanceRepository operations."""
    
    async def test_create_session(self, test_db_session, sample_session_data):
        """Test creating attendance session."""
        repo = AttendanceRepository(test_db_session)
        
        session = AttendanceSession(**sample_session_data)
        db_session = await repo.create_session(session)
        
        assert db_session.session_id == "SES001"
        assert db_session.class_id == "CS101"
        assert db_session.is_active is True
    
    async def test_get_session_by_id(self, test_db_session, sample_session_data):
        """Test getting session by ID."""
        repo = AttendanceRepository(test_db_session)
        
        # Create session
        session = AttendanceSession(**sample_session_data)
        await repo.create_session(session)
        await test_db_session.commit()
        
        # Get session
        db_session = await repo.get_session_by_id("SES001")
        
        assert db_session is not None
        assert db_session.session_id == "SES001"
        assert db_session.class_id == "CS101"
    
    async def test_create_attendance_record(self, test_db_session, sample_student_data, sample_session_data, sample_attendance_record, sample_face_embedding):
        """Test creating attendance record."""
        student_repo = StudentRepository(test_db_session)
        attendance_repo = AttendanceRepository(test_db_session)
        
        # Create student and session
        student = Student(
            **sample_student_data,
            face_embedding=sample_face_embedding.tobytes()
        )
        await student_repo.create_student(student)
        
        session = AttendanceSession(**sample_session_data)
        await attendance_repo.create_session(session)
        
        # Create attendance record
        record = AttendanceRecord(**sample_attendance_record)
        db_record = await attendance_repo.create_attendance_record(record)
        
        assert db_record.student_id == "STU001"
        assert db_record.session_id == "SES001"
        assert db_record.status == AttendanceStatus.PRESENT
    
    async def test_end_session(self, test_db_session, sample_session_data):
        """Test ending attendance session."""
        repo = AttendanceRepository(test_db_session)
        
        # Create session
        session = AttendanceSession(**sample_session_data)
        await repo.create_session(session)
        await test_db_session.commit()
        
        # End session
        success = await repo.end_session("SES001")
        await test_db_session.commit()
        
        assert success is True
        
        # Verify session ended
        ended_session = await repo.get_session_by_id("SES001")
        assert ended_session.is_active is False
        assert ended_session.end_time is not None
    
    async def test_get_active_sessions(self, test_db_session):
        """Test getting active sessions."""
        repo = AttendanceRepository(test_db_session)
        
        # Create multiple sessions
        sessions_data = [
            {
                "session_id": "SES001",
                "class_id": "CS101",
                "faculty_id": "FAC001",
                "start_time": datetime.now(),
                "is_active": True
            },
            {
                "session_id": "SES002",
                "class_id": "CS102", 
                "faculty_id": "FAC002",
                "start_time": datetime.now(),
                "is_active": True
            },
            {
                "session_id": "SES003",
                "class_id": "CS103",
                "faculty_id": "FAC003",
                "start_time": datetime.now(),
                "is_active": False
            }
        ]
        
        for session_data in sessions_data:
            session = AttendanceSession(**session_data)
            await repo.create_session(session)
        
        await test_db_session.commit()
        
        # Get active sessions
        active_sessions = await repo.get_active_sessions()
        
        assert len(active_sessions) == 2
        assert all(s.is_active for s in active_sessions)
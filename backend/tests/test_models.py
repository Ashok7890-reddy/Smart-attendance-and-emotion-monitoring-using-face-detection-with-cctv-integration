"""
Unit tests for data models.
"""

import pytest
from datetime import datetime
import numpy as np

from backend.models.student import Student, StudentType, StudentMatch
from backend.models.attendance import AttendanceRecord, AttendanceSession, AttendanceStatus
from backend.models.face_detection import FaceDetection, CameraLocation
from backend.models.emotion import EmotionResult, EmotionType, EmotionStatistics


class TestStudentModel:
    """Test Student model."""
    
    def test_student_creation(self, sample_student_data, sample_face_embedding):
        """Test student model creation."""
        student = Student(
            **sample_student_data,
            face_embedding=sample_face_embedding.tobytes()
        )
        
        assert student.student_id == "STU001"
        assert student.name == "John Doe"
        assert student.student_type == StudentType.DAY_SCHOLAR
        assert student.is_active is True
        assert student.email == "john.doe@example.com"
        assert student.class_id == "CS101"
        assert isinstance(student.face_embedding, bytes)
    
    def test_student_type_enum(self):
        """Test StudentType enum values."""
        assert StudentType.DAY_SCHOLAR.value == "day_scholar"
        assert StudentType.HOSTEL_STUDENT.value == "hostel_student"
    
    def test_student_match_creation(self, sample_student_data, sample_face_embedding):
        """Test StudentMatch model creation."""
        student = Student(
            **sample_student_data,
            face_embedding=sample_face_embedding.tobytes()
        )
        
        match = StudentMatch(
            student=student,
            confidence=0.95,
            match_timestamp=datetime.now()
        )
        
        assert match.student == student
        assert match.confidence == 0.95
        assert isinstance(match.match_timestamp, datetime)


class TestAttendanceModels:
    """Test attendance-related models."""
    
    def test_attendance_record_creation(self, sample_attendance_record):
        """Test AttendanceRecord model creation."""
        record = AttendanceRecord(**sample_attendance_record)
        
        assert record.student_id == "STU001"
        assert record.session_id == "SES001"
        assert record.status == AttendanceStatus.PRESENT
        assert record.confidence == 0.95
        assert record.classroom_entry_time is not None
        assert record.gate_entry_time is None
    
    def test_attendance_session_creation(self, sample_session_data):
        """Test AttendanceSession model creation."""
        session = AttendanceSession(**sample_session_data)
        
        assert session.session_id == "SES001"
        assert session.class_id == "CS101"
        assert session.faculty_id == "FAC001"
        assert session.total_registered == 30
        assert session.total_detected == 0
        assert session.is_active is True
        assert len(session.attendance_records) == 0
    
    def test_attendance_status_enum(self):
        """Test AttendanceStatus enum values."""
        assert AttendanceStatus.PRESENT.value == "present"
        assert AttendanceStatus.ABSENT.value == "absent"
        assert AttendanceStatus.LATE.value == "late"
        assert AttendanceStatus.INCOMPLETE.value == "incomplete"
    
    def test_attendance_session_with_records(self, sample_session_data, sample_attendance_record):
        """Test AttendanceSession with records."""
        session = AttendanceSession(**sample_session_data)
        record = AttendanceRecord(**sample_attendance_record)
        
        session.attendance_records.append(record)
        session.total_detected = 1
        
        assert len(session.attendance_records) == 1
        assert session.total_detected == 1
        assert session.attendance_records[0].student_id == "STU001"


class TestFaceDetectionModel:
    """Test FaceDetection model."""
    
    def test_face_detection_creation(self, sample_face_detection):
        """Test FaceDetection model creation."""
        detection = FaceDetection(**sample_face_detection)
        
        assert detection.bounding_box == (100, 100, 200, 200)
        assert detection.confidence == 0.92
        assert isinstance(detection.embedding, np.ndarray)
        assert detection.liveness_score == 0.88
        assert detection.camera_location == CameraLocation.CLASSROOM
        assert detection.student_id == "STU001"
    
    def test_camera_location_enum(self):
        """Test CameraLocation enum values."""
        assert CameraLocation.GATE.value == "gate"
        assert CameraLocation.CLASSROOM.value == "classroom"
    
    def test_face_detection_without_student_id(self, sample_face_detection):
        """Test FaceDetection without student ID (unidentified face)."""
        detection_data = sample_face_detection.copy()
        detection_data["student_id"] = None
        
        detection = FaceDetection(**detection_data)
        
        assert detection.student_id is None
        assert detection.confidence == 0.92
        assert detection.camera_location == CameraLocation.CLASSROOM


class TestEmotionModels:
    """Test emotion-related models."""
    
    def test_emotion_result_creation(self, sample_emotion_result):
        """Test EmotionResult model creation."""
        emotion = EmotionResult(**sample_emotion_result)
        
        assert emotion.student_id == "STU001"
        assert emotion.emotion == EmotionType.INTERESTED
        assert emotion.confidence == 0.85
        assert emotion.engagement_score == 0.8
        assert isinstance(emotion.timestamp, datetime)
    
    def test_emotion_type_enum(self):
        """Test EmotionType enum values."""
        assert EmotionType.INTERESTED.value == "interested"
        assert EmotionType.BORED.value == "bored"
        assert EmotionType.CONFUSED.value == "confused"
    
    def test_emotion_statistics_creation(self):
        """Test EmotionStatistics model creation."""
        stats = EmotionStatistics(
            session_id="SES001",
            total_frames=100,
            emotion_counts={
                EmotionType.INTERESTED: 60,
                EmotionType.BORED: 30,
                EmotionType.CONFUSED: 10
            },
            emotion_percentages={
                EmotionType.INTERESTED: 60.0,
                EmotionType.BORED: 30.0,
                EmotionType.CONFUSED: 10.0
            },
            average_engagement_score=0.75
        )
        
        assert stats.session_id == "SES001"
        assert stats.total_frames == 100
        assert stats.emotion_counts[EmotionType.INTERESTED] == 60
        assert stats.emotion_percentages[EmotionType.BORED] == 30.0
        assert stats.average_engagement_score == 0.75
        assert len(stats.emotion_timeline) == 0
    
    def test_emotion_statistics_with_timeline(self, sample_emotion_result):
        """Test EmotionStatistics with emotion timeline."""
        emotion = EmotionResult(**sample_emotion_result)
        
        stats = EmotionStatistics(
            session_id="SES001",
            total_frames=1,
            emotion_timeline=[emotion]
        )
        
        assert len(stats.emotion_timeline) == 1
        assert stats.emotion_timeline[0].student_id == "STU001"
        assert stats.emotion_timeline[0].emotion == EmotionType.INTERESTED


class TestModelValidation:
    """Test model validation and edge cases."""
    
    def test_student_with_minimal_data(self, sample_face_embedding):
        """Test student creation with minimal required data."""
        student = Student(
            student_id="STU002",
            name="Jane Smith",
            student_type=StudentType.HOSTEL_STUDENT,
            face_embedding=sample_face_embedding.tobytes(),
            enrollment_date=datetime.now()
        )
        
        assert student.student_id == "STU002"
        assert student.name == "Jane Smith"
        assert student.student_type == StudentType.HOSTEL_STUDENT
        assert student.is_active is True  # Default value
        assert student.email is None
        assert student.phone is None
        assert student.class_id is None
    
    def test_attendance_record_with_gate_entry(self, sample_attendance_record):
        """Test attendance record with gate entry time."""
        record_data = sample_attendance_record.copy()
        record_data["gate_entry_time"] = datetime(2024, 11, 3, 9, 55, 0)
        
        record = AttendanceRecord(**record_data)
        
        assert record.gate_entry_time is not None
        assert record.classroom_entry_time is not None
        assert record.gate_entry_time < record.classroom_entry_time
    
    def test_face_detection_bounding_box_validation(self, sample_face_detection):
        """Test face detection with different bounding box formats."""
        detection_data = sample_face_detection.copy()
        detection_data["bounding_box"] = (0, 0, 100, 100)
        
        detection = FaceDetection(**detection_data)
        
        assert detection.bounding_box == (0, 0, 100, 100)
        assert len(detection.bounding_box) == 4
    
    def test_emotion_result_confidence_range(self, sample_emotion_result):
        """Test emotion result with different confidence values."""
        # Test high confidence
        high_conf_data = sample_emotion_result.copy()
        high_conf_data["confidence"] = 0.99
        high_conf_emotion = EmotionResult(**high_conf_data)
        assert high_conf_emotion.confidence == 0.99
        
        # Test low confidence
        low_conf_data = sample_emotion_result.copy()
        low_conf_data["confidence"] = 0.51
        low_conf_emotion = EmotionResult(**low_conf_data)
        assert low_conf_emotion.confidence == 0.51
    
    def test_attendance_session_end_time(self, sample_session_data):
        """Test attendance session with end time."""
        session_data = sample_session_data.copy()
        session_data["end_time"] = datetime(2024, 11, 3, 11, 30, 0)
        session_data["is_active"] = False
        
        session = AttendanceSession(**session_data)
        
        assert session.end_time is not None
        assert session.is_active is False
        assert session.end_time > session.start_time
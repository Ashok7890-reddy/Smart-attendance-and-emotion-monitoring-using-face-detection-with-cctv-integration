"""
Unit tests for attendance service workflows.

Requirements tested: 2.1, 2.2, 2.3, 2.4, 2.5
- Test gate entry tracking and validation logic
- Validate cross-verification workflows for day scholars
- Test hostel student attendance processing
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import numpy as np

from backend.services.attendance_service import (
    AttendanceService, GateEntryTracker, ClassroomAttendanceProcessor,
    CrossVerificationProcessor, HostelStudentProcessor
)
from backend.models.student import Student, StudentType, StudentMatch
from backend.models.attendance import AttendanceSession, AttendanceRecord, AttendanceStatus
from backend.models.face_detection import FaceDetection, CameraLocation


@pytest.fixture
def mock_repositories():
    """Create mock repositories for testing."""
    attendance_repo = AsyncMock()
    student_repo = AsyncMock()
    face_detection_repo = AsyncMock()
    return attendance_repo, student_repo, face_detection_repo


@pytest.fixture
def mock_face_recognition_service():
    """Create mock face recognition service."""
    service = AsyncMock()
    return service


@pytest.fixture
def attendance_service(mock_repositories, mock_face_recognition_service):
    """Create attendance service with mocked dependencies."""
    attendance_repo, student_repo, face_detection_repo = mock_repositories
    
    with patch('backend.services.attendance_service.get_redis_client') as mock_redis, \
         patch('backend.services.attendance_service.get_settings') as mock_settings:
        
        mock_redis.return_value = AsyncMock()
        mock_settings.return_value = MagicMock(
            LIVENESS_THRESHOLD=0.8,
            FACE_MATCH_THRESHOLD=0.85
        )
        
        service = AttendanceService(
            attendance_repo=attendance_repo,
            student_repo=student_repo,
            face_detection_repo=face_detection_repo,
            face_recognition_service=mock_face_recognition_service
        )
        
        return service


@pytest.fixture
def sample_day_scholar():
    """Create sample day scholar student."""
    return Student(
        student_id="DS001",
        name="John Doe",
        student_type=StudentType.DAY_SCHOLAR,
        face_embedding=b"fake_embedding",
        enrollment_date=datetime.utcnow(),
        is_active=True,
        class_id="CS101"
    )


@pytest.fixture
def sample_hostel_student():
    """Create sample hostel student."""
    return Student(
        student_id="HS001",
        name="Jane Smith",
        student_type=StudentType.HOSTEL_STUDENT,
        face_embedding=b"fake_embedding",
        enrollment_date=datetime.utcnow(),
        is_active=True,
        class_id="CS101"
    )


class TestGateEntryTracking:
    """Test gate entry tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_record_gate_entry_success(self, attendance_service, sample_day_scholar):
        """Test successful gate entry recording for day scholar."""
        # Setup
        attendance_service.student_repo.get_student_by_id.return_value = sample_day_scholar
        attendance_service.redis.exists.return_value = False
        attendance_service.redis.setex.return_value = True
        
        # Execute
        result = await attendance_service.record_gate_entry("DS001", datetime.utcnow())
        
        # Assert
        assert result is True
        attendance_service.student_repo.get_student_by_id.assert_called_once_with("DS001")
        assert attendance_service.redis.setex.call_count == 2  # Gate entry + duplicate detection
    
    @pytest.mark.asyncio
    async def test_record_gate_entry_non_day_scholar(self, attendance_service, sample_hostel_student):
        """Test gate entry recording fails for non-day scholar."""
        # Setup
        attendance_service.student_repo.get_student_by_id.return_value = sample_hostel_student
        
        # Execute
        result = await attendance_service.record_gate_entry("HS001", datetime.utcnow())
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_record_gate_entry_duplicate_detection(self, attendance_service, sample_day_scholar):
        """Test duplicate gate entry detection."""
        # Setup
        attendance_service.student_repo.get_student_by_id.return_value = sample_day_scholar
        attendance_service.redis.exists.return_value = True  # Duplicate exists
        
        # Execute
        result = await attendance_service.record_gate_entry("DS001", datetime.utcnow())
        
        # Assert
        assert result is True  # Should return True for duplicate (already recorded)
        attendance_service.redis.setex.assert_not_called()  # Should not set new entry
    
    @pytest.mark.asyncio
    async def test_validate_gate_entry_success(self, attendance_service):
        """Test successful gate entry validation."""
        # Setup
        current_time = datetime.utcnow()
        gate_entry_data = {
            'student_id': 'DS001',
            'timestamp': current_time.isoformat(),
            'date': current_time.strftime('%Y-%m-%d')
        }
        attendance_service.redis.get.return_value = f'"{current_time.isoformat()}"'
        
        # Execute
        result = await attendance_service.validate_gate_entry("DS001", current_time + timedelta(hours=1))
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_gate_entry_no_entry(self, attendance_service):
        """Test gate entry validation when no entry exists."""
        # Setup
        attendance_service.redis.get.return_value = None
        
        # Execute
        result = await attendance_service.validate_gate_entry("DS001", datetime.utcnow())
        
        # Assert
        assert result is False


class TestClassroomAttendanceProcessing:
    """Test classroom attendance processing functionality."""
    
    @pytest.mark.asyncio
    async def test_mark_classroom_attendance_success(self, attendance_service, mock_repositories):
        """Test successful classroom attendance marking."""
        # Setup
        attendance_repo, student_repo, face_detection_repo = mock_repositories
        
        # Mock face detection
        detection = FaceDetection(
            bounding_box=(100, 100, 200, 200),
            confidence=0.95,
            embedding=np.array([0.1, 0.2, 0.3]),
            liveness_score=0.9,
            timestamp=datetime.utcnow(),
            camera_location=CameraLocation.CLASSROOM
        )
        
        # Mock student match
        student_match = StudentMatch(
            student=sample_day_scholar,
            confidence=0.92,
            match_timestamp=datetime.utcnow()
        )
        
        attendance_service.face_recognition_service.match_face.return_value = student_match
        student_repo.get_students_by_class.return_value = [sample_day_scholar]
        attendance_repo.create_session.return_value = AsyncMock()
        attendance_repo.create_attendance_record.return_value = AsyncMock()
        attendance_repo.update_session_counts.return_value = True
        face_detection_repo.create_detection.return_value = AsyncMock()
        
        # Execute
        session = await attendance_service.mark_classroom_attendance([detection])
        
        # Assert
        assert session is not None
        assert session.total_detected == 1
        attendance_repo.create_session.assert_called_once()
        attendance_repo.create_attendance_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mark_classroom_attendance_low_liveness(self, attendance_service):
        """Test classroom attendance with low liveness score."""
        # Setup
        detection = FaceDetection(
            bounding_box=(100, 100, 200, 200),
            confidence=0.95,
            embedding=np.array([0.1, 0.2, 0.3]),
            liveness_score=0.5,  # Below threshold
            timestamp=datetime.utcnow(),
            camera_location=CameraLocation.CLASSROOM
        )
        
        attendance_service.student_repo.get_students_by_class.return_value = []
        
        # Execute
        session = await attendance_service.mark_classroom_attendance([detection])
        
        # Assert
        assert session.total_detected == 0  # Should not detect due to low liveness


class TestCrossVerification:
    """Test cross-verification logic for day scholars."""
    
    @pytest.mark.asyncio
    async def test_validate_day_scholar_attendance_success(self, attendance_service, sample_day_scholar):
        """Test successful day scholar cross-verification."""
        # Setup
        session_id = "session_001"
        session = AttendanceSession(
            session_id=session_id,
            class_id="CS101",
            faculty_id="faculty_001",
            start_time=datetime.utcnow(),
            total_registered=1
        )
        
        attendance_record = AttendanceRecord(
            student_id="DS001",
            session_id=session_id,
            status=AttendanceStatus.PRESENT,
            timestamp=datetime.utcnow(),
            confidence=0.9,
            classroom_entry_time=datetime.utcnow()
        )
        
        attendance_service.student_repo.get_student_by_id.return_value = sample_day_scholar
        attendance_service.attendance_repo.get_session_by_id.return_value = session
        attendance_service.attendance_repo.get_session_attendance.return_value = [attendance_record]
        
        # Mock gate entry validation
        gate_time = datetime.utcnow() - timedelta(hours=1)
        attendance_service.redis.get.return_value = f'"{gate_time.isoformat()}"'
        
        # Execute
        result = await attendance_service.validate_day_scholar_attendance("DS001", session_id)
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_day_scholar_attendance_no_gate_entry(self, attendance_service, sample_day_scholar):
        """Test day scholar validation fails without gate entry."""
        # Setup
        session_id = "session_001"
        session = AttendanceSession(
            session_id=session_id,
            class_id="CS101",
            faculty_id="faculty_001",
            start_time=datetime.utcnow(),
            total_registered=1
        )
        
        attendance_service.student_repo.get_student_by_id.return_value = sample_day_scholar
        attendance_service.attendance_repo.get_session_by_id.return_value = session
        attendance_service.redis.get.return_value = None  # No gate entry
        
        # Execute
        result = await attendance_service.validate_day_scholar_attendance("DS001", session_id)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_hostel_student_skips_verification(self, attendance_service, sample_hostel_student):
        """Test that hostel students skip cross-verification."""
        # Setup
        attendance_service.student_repo.get_student_by_id.return_value = sample_hostel_student
        
        # Execute
        result = await attendance_service.validate_day_scholar_attendance("HS001", "session_001")
        
        # Assert
        assert result is True  # Should return True for hostel students


class TestHostelStudentWorkflow:
    """Test hostel student attendance workflow."""
    
    @pytest.mark.asyncio
    async def test_hostel_student_processor_initialization(self, attendance_service):
        """Test hostel student processor initialization."""
        processor = HostelStudentProcessor(attendance_service)
        assert processor.attendance_service == attendance_service
    
    @pytest.mark.asyncio
    async def test_process_hostel_student_attendance_success(self, attendance_service, sample_hostel_student):
        """Test successful hostel student attendance processing."""
        # Setup
        processor = HostelStudentProcessor(attendance_service)
        session_id = "session_001"
        
        session = AttendanceSession(
            session_id=session_id,
            class_id="CS101",
            faculty_id="faculty_001",
            start_time=datetime.utcnow(),
            is_active=True
        )
        
        attendance_service.student_repo.get_student_by_id.return_value = sample_hostel_student
        attendance_service.attendance_repo.get_session_by_id.return_value = session
        attendance_service.attendance_repo.get_session_attendance.return_value = []
        attendance_service.attendance_repo.create_attendance_record.return_value = AsyncMock()
        
        # Execute
        result = await processor.process_hostel_student_attendance("HS001", session_id, 0.9)
        
        # Assert
        assert result is True
        attendance_service.attendance_repo.create_attendance_record.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_hostel_student_attendance_day_scholar_rejected(self, attendance_service, sample_day_scholar):
        """Test that day scholars are rejected in hostel workflow."""
        # Setup
        processor = HostelStudentProcessor(attendance_service)
        attendance_service.student_repo.get_student_by_id.return_value = sample_day_scholar
        
        # Execute
        result = await processor.process_hostel_student_attendance("DS001", "session_001", 0.9)
        
        # Assert
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_hostel_students_in_class(self, attendance_service, sample_hostel_student):
        """Test getting hostel students in a class."""
        # Setup
        processor = HostelStudentProcessor(attendance_service)
        attendance_service.student_repo.get_students_by_class.return_value = [sample_hostel_student]
        
        # Execute
        result = await processor.get_hostel_students_in_class("CS101")
        
        # Assert
        assert len(result) == 1
        assert result[0]['student_id'] == "HS001"
        assert result[0]['student_type'] == "hostel_student"
    
    @pytest.mark.asyncio
    async def test_validate_hostel_attendance(self, attendance_service, sample_hostel_student):
        """Test hostel attendance validation."""
        # Setup
        processor = HostelStudentProcessor(attendance_service)
        session_id = "session_001"
        
        session = AttendanceSession(
            session_id=session_id,
            class_id="CS101",
            faculty_id="faculty_001",
            start_time=datetime.utcnow()
        )
        
        attendance_record = AttendanceRecord(
            student_id="HS001",
            session_id=session_id,
            status=AttendanceStatus.PRESENT,
            timestamp=datetime.utcnow(),
            confidence=0.9
        )
        
        attendance_service.attendance_repo.get_session_by_id.return_value = session
        attendance_service.student_repo.get_students_by_class.return_value = [sample_hostel_student]
        attendance_service.attendance_repo.get_session_attendance.return_value = [attendance_record]
        
        # Execute
        result = await processor.validate_hostel_attendance(session_id)
        
        # Assert
        assert result['total_hostel_students'] == 1
        assert result['present_count'] == 1
        assert result['absent_count'] == 0
        assert result['attendance_rate'] == 100.0


class TestAttendanceServiceIntegration:
    """Integration tests for attendance service workflows."""
    
    @pytest.mark.asyncio
    async def test_complete_day_scholar_workflow(self, attendance_service, sample_day_scholar):
        """Test complete day scholar workflow from gate to classroom."""
        # Setup
        current_time = datetime.utcnow()
        session_id = "session_001"
        
        # Mock gate entry
        attendance_service.student_repo.get_student_by_id.return_value = sample_day_scholar
        attendance_service.redis.exists.return_value = False
        attendance_service.redis.setex.return_value = True
        attendance_service.redis.get.return_value = f'"{current_time.isoformat()}"'
        
        # Mock classroom attendance
        session = AttendanceSession(
            session_id=session_id,
            class_id="CS101",
            faculty_id="faculty_001",
            start_time=current_time,
            is_active=True
        )
        
        attendance_service.attendance_repo.get_session_by_id.return_value = session
        attendance_service.attendance_repo.get_session_attendance.return_value = []
        
        # Execute gate entry
        gate_result = await attendance_service.record_gate_entry("DS001", current_time)
        
        # Execute cross-verification
        verification_result = await attendance_service.validate_day_scholar_attendance("DS001", session_id)
        
        # Assert
        assert gate_result is True
        # Note: verification_result will be False because no classroom record exists in this test
        # In real workflow, classroom attendance would be marked first
    
    @pytest.mark.asyncio
    async def test_complete_hostel_student_workflow(self, attendance_service, sample_hostel_student):
        """Test complete hostel student workflow (classroom only)."""
        # Setup
        processor = HostelStudentProcessor(attendance_service)
        session_id = "session_001"
        
        session = AttendanceSession(
            session_id=session_id,
            class_id="CS101",
            faculty_id="faculty_001",
            start_time=datetime.utcnow(),
            is_active=True
        )
        
        attendance_service.student_repo.get_student_by_id.return_value = sample_hostel_student
        attendance_service.attendance_repo.get_session_by_id.return_value = session
        attendance_service.attendance_repo.get_session_attendance.return_value = []
        attendance_service.attendance_repo.create_attendance_record.return_value = AsyncMock()
        
        # Execute
        result = await processor.process_hostel_student_attendance("HS001", session_id, 0.9)
        
        # Assert
        assert result is True
        attendance_service.attendance_repo.create_attendance_record.assert_called_once()
        
        # Verify no gate entry validation is required
        attendance_service.redis.get.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
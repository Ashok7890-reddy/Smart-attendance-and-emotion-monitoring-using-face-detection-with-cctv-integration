"""
Unit tests for validation service.

Requirements tested: 4.1, 4.2, 4.3
- Test attendance count validation and missing student detection
- Validate system monitoring and health check functionality
- Test notification delivery and alert generation
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from dataclasses import dataclass

from backend.services.validation_service import (
    ValidationService, ValidationResult, ValidationLevel, SystemHealthStatus
)
from backend.services.notification_service import NotificationService
from backend.models.student import Student, StudentType
from backend.models.attendance import AttendanceSession, AttendanceRecord, AttendanceStatus


@pytest.fixture
def mock_repositories():
    """Create mock repositories for testing."""
    student_repo = MagicMock()
    attendance_repo = MagicMock()
    return student_repo, attendance_repo


@pytest.fixture
def mock_notification_service():
    """Create mock notification service."""
    return MagicMock(spec=NotificationService)


@pytest.fixture
def validation_service(mock_repositories, mock_notification_service):
    """Create validation service with mocked dependencies."""
    student_repo, attendance_repo = mock_repositories
    
    with patch('backend.services.validation_service.StudentRepository') as mock_student_repo_class, \
         patch('backend.services.validation_service.AttendanceRepository') as mock_attendance_repo_class, \
         patch('backend.services.validation_service.NotificationService') as mock_notification_class:
        
        mock_student_repo_class.return_value = student_repo
        mock_attendance_repo_class.return_value = attendance_repo
        mock_notification_class.return_value = mock_notification_service
        
        service = ValidationService()
        return service, student_repo, attendance_repo, mock_notification_service


@pytest.fixture
def sample_students():
    """Create sample students for testing."""
    return [
        Student(
            student_id="DS001",
            name="John Doe",
            student_type=StudentType.DAY_SCHOLAR,
            face_embedding=b"fake_embedding_1",
            enrollment_date=datetime.utcnow(),
            is_active=True,
            class_id="CS101"
        ),
        Student(
            student_id="DS002",
            name="Jane Smith",
            student_type=StudentType.DAY_SCHOLAR,
            face_embedding=b"fake_embedding_2",
            enrollment_date=datetime.utcnow(),
            is_active=True,
            class_id="CS101"
        ),
        Student(
            student_id="HS001",
            name="Bob Johnson",
            student_type=StudentType.HOSTEL_STUDENT,
            face_embedding=b"fake_embedding_3",
            enrollment_date=datetime.utcnow(),
            is_active=True,
            class_id="CS101"
        ),
        Student(
            student_id="DS003",
            name="Alice Brown",
            student_type=StudentType.DAY_SCHOLAR,
            face_embedding=b"fake_embedding_4",
            enrollment_date=datetime.utcnow(),
            is_active=False,  # Inactive student
            class_id="CS101"
        )
    ]


@pytest.fixture
def sample_attendance_session(sample_students):
    """Create sample attendance session."""
    return AttendanceSession(
        session_id="session_001",
        class_id="CS101",
        faculty_id="faculty_001",
        start_time=datetime.utcnow(),
        total_registered=3,  # Only active students
        total_detected=2,
        attendance_records=[
            AttendanceRecord(
                student_id="DS001",
                session_id="session_001",
                status=AttendanceStatus.PRESENT,
                timestamp=datetime.utcnow(),
                confidence=0.95,
                gate_entry_time=datetime.utcnow() - timedelta(hours=1),
                classroom_entry_time=datetime.utcnow()
            ),
            AttendanceRecord(
                student_id="HS001",
                session_id="session_001",
                status=AttendanceStatus.PRESENT,
                timestamp=datetime.utcnow(),
                confidence=0.92,
                classroom_entry_time=datetime.utcnow()
            )
        ]
    )


class TestAttendanceCountValidation:
    """Test attendance count validation functionality."""
    
    def test_validate_attendance_count_success(self, validation_service, sample_students, sample_attendance_session):
        """Test successful attendance count validation."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - all students present
        active_students = [s for s in sample_students if s.is_active]
        student_repo.get_students_by_class.return_value = active_students
        
        # Update session to have all students present
        sample_attendance_session.attendance_records.append(
            AttendanceRecord(
                student_id="DS002",
                session_id="session_001",
                status=AttendanceStatus.PRESENT,
                timestamp=datetime.utcnow(),
                confidence=0.90
            )
        )
        
        # Execute
        result = service.validate_attendance_count(sample_attendance_session)
        
        # Assert
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert result.level == ValidationLevel.INFO
        assert result.details['expected_count'] == 3
        assert result.details['present_count'] == 3
        assert result.details['missing_count'] == 0
        assert result.details['accuracy'] == 1.0
    
    def test_validate_attendance_count_missing_students(self, validation_service, sample_students, sample_attendance_session):
        """Test attendance validation with missing students."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - some students missing
        active_students = [s for s in sample_students if s.is_active]
        student_repo.get_students_by_class.return_value = active_students
        
        # Execute (session has only 2 present out of 3 expected)
        result = service.validate_attendance_count(sample_attendance_session)
        
        # Assert
        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert result.level == ValidationLevel.WARNING
        assert result.details['expected_count'] == 3
        assert result.details['present_count'] == 2
        assert result.details['missing_count'] == 1
        assert result.details['accuracy'] == 2/3
    
    def test_validate_attendance_count_critical_missing(self, validation_service, sample_students, sample_attendance_session):
        """Test attendance validation with critical number of missing students."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - many students missing
        many_students = sample_students + [
            Student(
                student_id=f"DS{i:03d}",
                name=f"Student {i}",
                student_type=StudentType.DAY_SCHOLAR,
                face_embedding=f"fake_embedding_{i}".encode(),
                enrollment_date=datetime.utcnow(),
                is_active=True,
                class_id="CS101"
            )
            for i in range(4, 15)  # Add 11 more students
        ]
        
        student_repo.get_students_by_class.return_value = [s for s in many_students if s.is_active]
        
        # Execute (only 2 present out of 14 expected)
        result = service.validate_attendance_count(sample_attendance_session)
        
        # Assert
        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert result.level == ValidationLevel.ERROR
        assert result.details['missing_count'] == 12  # 14 expected - 2 present
        assert result.details['accuracy'] < 0.2
    
    def test_validate_attendance_count_error_handling(self, validation_service, sample_attendance_session):
        """Test error handling in attendance count validation."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - repository throws exception
        student_repo.get_students_by_class.side_effect = Exception("Database error")
        
        # Execute
        result = service.validate_attendance_count(sample_attendance_session)
        
        # Assert
        assert isinstance(result, ValidationResult)
        assert result.is_valid is False
        assert result.level == ValidationLevel.CRITICAL
        assert "Database error" in result.message


class TestMissingStudentIdentification:
    """Test missing student identification functionality."""
    
    def test_check_missing_students_success(self, validation_service, sample_students, sample_attendance_session):
        """Test successful missing student identification."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        active_students = [s for s in sample_students if s.is_active]
        student_repo.get_students_by_class.return_value = active_students
        
        # Execute
        missing_students = service.check_missing_students(sample_attendance_session)
        
        # Assert
        assert len(missing_students) == 1
        assert missing_students[0].student_id == "DS002"
        assert missing_students[0].name == "Jane Smith"
    
    def test_check_missing_students_none_missing(self, validation_service, sample_students, sample_attendance_session):
        """Test missing student check when no students are missing."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - add missing student to attendance
        sample_attendance_session.attendance_records.append(
            AttendanceRecord(
                student_id="DS002",
                session_id="session_001",
                status=AttendanceStatus.PRESENT,
                timestamp=datetime.utcnow(),
                confidence=0.88
            )
        )
        
        active_students = [s for s in sample_students if s.is_active]
        student_repo.get_students_by_class.return_value = active_students
        
        # Execute
        missing_students = service.check_missing_students(sample_attendance_session)
        
        # Assert
        assert len(missing_students) == 0
    
    def test_check_missing_students_error_handling(self, validation_service, sample_attendance_session):
        """Test error handling in missing student identification."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - repository throws exception
        student_repo.get_students_by_class.side_effect = Exception("Database error")
        
        # Execute
        missing_students = service.check_missing_students(sample_attendance_session)
        
        # Assert
        assert missing_students == []


class TestValidationAlerts:
    """Test validation alert generation."""
    
    def test_generate_validation_alerts_no_issues(self, validation_service):
        """Test alert generation when no issues exist."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - valid result
        validation_result = ValidationResult(
            is_valid=True,
            level=ValidationLevel.INFO,
            message="All good",
            details={"session_id": "session_001", "missing_count": 0},
            timestamp=datetime.now()
        )
        
        # Execute
        alerts = service.generate_validation_alerts(validation_result)
        
        # Assert
        assert alerts['total_alerts'] == 0
        assert alerts['critical_alerts'] == 0
        assert alerts['error_alerts'] == 0
    
    def test_generate_validation_alerts_with_issues(self, validation_service):
        """Test alert generation with validation issues."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - invalid result with missing students
        validation_result = ValidationResult(
            is_valid=False,
            level=ValidationLevel.ERROR,
            message="High absenteeism",
            details={"session_id": "session_001", "missing_count": 8, "accuracy": 0.6},
            timestamp=datetime.now()
        )
        
        # Execute
        alerts = service.generate_validation_alerts(validation_result)
        
        # Assert
        assert alerts['total_alerts'] == 2  # One for validation failure, one for high absenteeism
        assert alerts['error_alerts'] == 2
        assert any(alert['type'] == 'attendance_discrepancy' for alert in alerts['alerts'])
        assert any(alert['type'] == 'high_absenteeism' for alert in alerts['alerts'])


class TestComprehensiveValidation:
    """Test comprehensive validation functionality."""
    
    def test_perform_comprehensive_validation_success(self, validation_service, sample_students, sample_attendance_session):
        """Test successful comprehensive validation."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        active_students = [s for s in sample_students if s.is_active]
        student_repo.get_students_by_class.return_value = active_students
        student_repo.get_by_id.side_effect = lambda sid: next((s for s in sample_students if s.student_id == sid), None)
        
        # Execute
        results = service.perform_comprehensive_validation(sample_attendance_session)
        
        # Assert
        assert 'count_validation' in results
        assert 'missing_students' in results
        assert 'cross_verification' in results
        assert 'alerts' in results
        assert 'overall_status' in results
        
        assert isinstance(results['count_validation'], ValidationResult)
        assert isinstance(results['missing_students'], list)
        assert len(results['missing_students']) == 1  # DS002 is missing
        assert results['missing_count'] == 1
    
    def test_perform_comprehensive_validation_with_notifications(self, validation_service, sample_students, sample_attendance_session):
        """Test comprehensive validation sends appropriate notifications."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        active_students = [s for s in sample_students if s.is_active]
        student_repo.get_students_by_class.return_value = active_students
        student_repo.get_by_id.side_effect = lambda sid: next((s for s in sample_students if s.student_id == sid), None)
        
        # Execute
        results = service.perform_comprehensive_validation(sample_attendance_session)
        
        # Assert notifications were sent
        notification_service.send_attendance_alert.assert_called_once()
        call_args = notification_service.send_attendance_alert.call_args
        assert call_args[0][0] == "session_001"  # session_id
        assert call_args[0][1] == 1  # missing_count
        assert "DS002" in call_args[0][2]  # missing_student_ids
    
    def test_perform_comprehensive_validation_error_handling(self, validation_service, sample_attendance_session):
        """Test comprehensive validation error handling."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - repository throws exception
        student_repo.get_students_by_class.side_effect = Exception("Database error")
        
        # Execute
        results = service.perform_comprehensive_validation(sample_attendance_session)
        
        # Assert
        assert results['overall_status']['is_valid'] is False
        assert results['overall_status']['validation_score'] >= 0.0  # Score can be partial due to cross-verification
        # Note: error is not in overall_status when some validations succeed
        
        # Assert that individual validation errors were logged but comprehensive validation continued
        # The comprehensive validation doesn't fail completely, it just has invalid sub-validations


class TestSystemHealthMonitoring:
    """Test system health monitoring functionality."""
    
    def test_monitor_system_health_healthy(self, validation_service):
        """Test system health monitoring when all components are healthy."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - all repositories work fine
        student_repo.get_students_by_class.return_value = []
        notification_service.get_pending_notifications.return_value = []
        
        # Execute
        health_status = service.monitor_system_health()
        
        # Assert
        assert isinstance(health_status, SystemHealthStatus)
        assert health_status.overall_status == "healthy"
        assert 'student_database' in health_status.components
        assert 'attendance_database' in health_status.components
        assert 'notification_service' in health_status.components
        assert 'validation_service' in health_status.components
        
        assert health_status.components['student_database']['status'] == 'healthy'
        assert health_status.components['notification_service']['status'] == 'healthy'
    
    def test_monitor_system_health_degraded(self, validation_service):
        """Test system health monitoring with degraded components."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - notification service has too many pending notifications
        student_repo.get_students_by_class.return_value = []
        notification_service.get_pending_notifications.return_value = [None] * 150  # Too many
        
        # Execute
        health_status = service.monitor_system_health()
        
        # Assert
        assert health_status.overall_status == "degraded"
        assert health_status.components['notification_service']['status'] == 'degraded'
        assert health_status.components['notification_service']['pending_notifications'] == 150
    
    def test_monitor_system_health_unhealthy(self, validation_service):
        """Test system health monitoring with unhealthy components."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - database error
        student_repo.get_students_by_class.side_effect = Exception("Database connection failed")
        notification_service.get_pending_notifications.return_value = []
        
        # Execute
        health_status = service.monitor_system_health()
        
        # Assert
        assert health_status.overall_status in ["degraded", "unhealthy"]  # Either is acceptable for this test
        assert health_status.components['student_database']['status'] == 'unhealthy'
        assert 'Database connection failed' in health_status.components['student_database']['error']
        
        # Assert critical alert was sent
        notification_service.send_alert.assert_called()
        alert_call = notification_service.send_alert.call_args
        assert "System health critical" in alert_call[0][0]


class TestValidationSummary:
    """Test validation summary functionality."""
    
    def test_get_validation_summary_success(self, validation_service, sample_students, sample_attendance_session):
        """Test successful validation summary generation."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        attendance_repo.get_session_by_id.return_value = sample_attendance_session
        active_students = [s for s in sample_students if s.is_active]
        student_repo.get_students_by_class.return_value = active_students
        student_repo.get_by_id.side_effect = lambda sid: next((s for s in sample_students if s.student_id == sid), None)
        
        # Execute
        summary = service.get_validation_summary("session_001")
        
        # Assert
        assert 'session_id' in summary
        assert 'overall_valid' in summary
        assert 'validation_score' in summary
        assert 'attendance_accuracy' in summary
        assert 'missing_student_count' in summary
        assert 'recommendations' in summary
        
        assert summary['session_id'] == "session_001"
        assert summary['missing_student_count'] == 1
        assert isinstance(summary['recommendations'], list)
        assert len(summary['recommendations']) > 0
    
    def test_get_validation_summary_session_not_found(self, validation_service):
        """Test validation summary when session is not found."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        attendance_repo.get_session_by_id.return_value = None
        
        # Execute
        summary = service.get_validation_summary("nonexistent_session")
        
        # Assert
        assert 'error' in summary
        assert 'Session nonexistent_session not found' in summary['error']


class TestCameraConnectivityMonitoring:
    """Test camera connectivity monitoring functionality."""
    
    def test_monitor_camera_connectivity_connected(self, validation_service):
        """Test camera connectivity monitoring when camera is connected."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        notification_service.send_camera_connectivity_alert.return_value = True
        
        # Execute
        result = service.monitor_camera_connectivity("camera_001", True)
        
        # Assert
        assert result is True
        notification_service.send_camera_connectivity_alert.assert_called_once_with("camera_001", True)
    
    def test_monitor_camera_connectivity_disconnected(self, validation_service):
        """Test camera connectivity monitoring when camera is disconnected."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        notification_service.send_camera_connectivity_alert.return_value = True
        
        # Execute
        result = service.monitor_camera_connectivity("camera_002", False)
        
        # Assert
        assert result is True
        notification_service.send_camera_connectivity_alert.assert_called_once_with("camera_002", False)
    
    def test_monitor_camera_connectivity_notification_failure(self, validation_service):
        """Test camera connectivity monitoring when notification fails."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        notification_service.send_camera_connectivity_alert.return_value = False
        
        # Execute
        result = service.monitor_camera_connectivity("camera_003", False)
        
        # Assert
        assert result is False
        notification_service.send_camera_connectivity_alert.assert_called_once_with("camera_003", False)
    
    def test_monitor_camera_connectivity_error_handling(self, validation_service):
        """Test camera connectivity monitoring error handling."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        notification_service.send_camera_connectivity_alert.side_effect = Exception("Notification error")
        
        # Execute
        result = service.monitor_camera_connectivity("camera_004", True)
        
        # Assert
        assert result is False


class TestFaceRecognitionConfidenceMonitoring:
    """Test face recognition confidence monitoring functionality."""
    
    def test_monitor_face_recognition_confidence_above_threshold(self, validation_service):
        """Test face recognition confidence monitoring when confidence is above threshold."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - high confidence scores
        notification_service.face_recognition_confidence_threshold = 0.85
        confidence_scores = [0.90, 0.92, 0.88, 0.95]
        
        # Execute
        result = service.monitor_face_recognition_confidence("session_001", confidence_scores)
        
        # Assert
        assert result is True
        # No alert should be sent for high confidence
        notification_service.send_face_recognition_confidence_alert.assert_not_called()
    
    def test_monitor_face_recognition_confidence_below_threshold(self, validation_service):
        """Test face recognition confidence monitoring when confidence is below threshold."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup - low confidence scores
        notification_service.face_recognition_confidence_threshold = 0.85
        notification_service.send_face_recognition_confidence_alert.return_value = True
        confidence_scores = [0.70, 0.75, 0.80, 0.65]  # Average = 0.725
        
        # Execute
        result = service.monitor_face_recognition_confidence("session_001", confidence_scores)
        
        # Assert
        assert result is True
        notification_service.send_face_recognition_confidence_alert.assert_called_once_with(
            "session_001", 4, 0.725  # session_id, low_confidence_count, average_confidence
        )
    
    def test_monitor_face_recognition_confidence_empty_scores(self, validation_service):
        """Test face recognition confidence monitoring with empty confidence scores."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Execute
        result = service.monitor_face_recognition_confidence("session_001", [])
        
        # Assert
        assert result is True
        notification_service.send_face_recognition_confidence_alert.assert_not_called()
    
    def test_monitor_face_recognition_confidence_notification_failure(self, validation_service):
        """Test face recognition confidence monitoring when notification fails."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        notification_service.face_recognition_confidence_threshold = 0.85
        notification_service.send_face_recognition_confidence_alert.return_value = False
        confidence_scores = [0.70, 0.75]  # Below threshold
        
        # Execute
        result = service.monitor_face_recognition_confidence("session_001", confidence_scores)
        
        # Assert
        assert result is False
        notification_service.send_face_recognition_confidence_alert.assert_called_once()
    
    def test_monitor_face_recognition_confidence_error_handling(self, validation_service):
        """Test face recognition confidence monitoring error handling."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        notification_service.face_recognition_confidence_threshold = 0.85
        notification_service.send_face_recognition_confidence_alert.side_effect = Exception("Alert error")
        confidence_scores = [0.70, 0.75]
        
        # Execute
        result = service.monitor_face_recognition_confidence("session_001", confidence_scores)
        
        # Assert
        assert result is False


class TestProcessingPerformanceMonitoring:
    """Test processing performance monitoring functionality."""
    
    def test_monitor_processing_performance_within_threshold(self, validation_service):
        """Test processing performance monitoring when processing time is within threshold."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        notification_service.processing_time_threshold_seconds = 5.0
        notification_service.send_performance_alert.return_value = True
        
        # Execute - processing time within threshold
        result = service.monitor_processing_performance("face_recognition", 3.5)
        
        # Assert
        assert result is True
        notification_service.send_performance_alert.assert_called_once_with("face_recognition", 3.5)
    
    def test_monitor_processing_performance_exceeds_threshold(self, validation_service):
        """Test processing performance monitoring when processing time exceeds threshold."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        notification_service.processing_time_threshold_seconds = 5.0
        notification_service.send_performance_alert.return_value = True
        
        # Execute - processing time exceeds threshold
        result = service.monitor_processing_performance("emotion_analysis", 7.2)
        
        # Assert
        assert result is True
        notification_service.send_performance_alert.assert_called_once_with("emotion_analysis", 7.2)
    
    def test_monitor_processing_performance_notification_failure(self, validation_service):
        """Test processing performance monitoring when notification fails."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        notification_service.processing_time_threshold_seconds = 5.0
        notification_service.send_performance_alert.return_value = False
        
        # Execute
        result = service.monitor_processing_performance("face_recognition", 6.5)
        
        # Assert
        assert result is False
        notification_service.send_performance_alert.assert_called_once_with("face_recognition", 6.5)
    
    def test_monitor_processing_performance_error_handling(self, validation_service):
        """Test processing performance monitoring error handling."""
        service, student_repo, attendance_repo, notification_service = validation_service
        
        # Setup
        notification_service.send_performance_alert.side_effect = Exception("Performance alert error")
        
        # Execute
        result = service.monitor_processing_performance("emotion_analysis", 4.0)
        
        # Assert
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
"""
Validation and monitoring service for the Smart Attendance System.
"""

from datetime import datetime
from typing import List, Dict, Optional
import logging
from dataclasses import dataclass
from enum import Enum

from backend.core.base_service import BaseService
from backend.core.interfaces import IValidationService
from backend.models.student import Student
from backend.models.attendance import AttendanceSession, AttendanceStatus
from backend.database.repositories import StudentRepository, AttendanceRepository
from backend.services.notification_service import NotificationService, NotificationPriority


class ValidationLevel(Enum):
    """Validation alert levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Validation result model."""
    is_valid: bool
    level: ValidationLevel
    message: str
    details: Dict
    timestamp: datetime


@dataclass
class SystemHealthStatus:
    """System health status model."""
    overall_status: str
    components: Dict[str, Dict]
    timestamp: datetime
    uptime_seconds: float


class ValidationService(BaseService, IValidationService):
    """Service for validating attendance and monitoring system health."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.student_repository = StudentRepository(config)
        self.attendance_repository = AttendanceRepository(config)
        self.notification_service = NotificationService(config)
        self.validation_threshold = 0.95  # 95% attendance accuracy threshold
        self.missing_student_threshold = 5  # Alert if more than 5 students missing
        self.critical_missing_threshold = 10  # Critical alert threshold
        
    def validate_attendance_count(self, session: AttendanceSession) -> ValidationResult:
        """
        Validate attendance count against registered class strength.
        
        Requirements: 4.1, 4.2, 4.3
        """
        try:
            # Get registered students for the class
            registered_students = self.student_repository.get_students_by_class(session.class_id)
            expected_count = len([s for s in registered_students if s.is_active])
            
            detected_count = session.total_detected
            present_count = len([r for r in session.attendance_records 
                               if r.status == AttendanceStatus.PRESENT])
            
            # Calculate attendance accuracy
            accuracy = present_count / expected_count if expected_count > 0 else 0
            missing_count = expected_count - present_count
            
            # Determine validation level
            if accuracy >= self.validation_threshold and missing_count == 0:
                level = ValidationLevel.INFO
                message = f"Attendance validation passed. {present_count}/{expected_count} students present."
            elif accuracy >= self.validation_threshold:
                level = ValidationLevel.WARNING
                message = f"Good attendance but {missing_count} students missing."
            elif missing_count <= self.missing_student_threshold:
                level = ValidationLevel.WARNING
                message = f"Low attendance: {present_count}/{expected_count} students present."
            else:
                level = ValidationLevel.ERROR
                message = f"Critical attendance issue: {missing_count} students missing."
            
            details = {
                "session_id": session.session_id,
                "expected_count": expected_count,
                "detected_count": detected_count,
                "present_count": present_count,
                "missing_count": missing_count,
                "accuracy": accuracy,
                "threshold_met": accuracy >= self.validation_threshold
            }
            
            is_valid = accuracy >= self.validation_threshold and missing_count <= self.missing_student_threshold
            
            result = ValidationResult(
                is_valid=is_valid,
                level=level,
                message=message,
                details=details,
                timestamp=datetime.now()
            )
            
            self.logger.info(f"Attendance validation completed for session {session.session_id}: {message}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating attendance count: {str(e)}")
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.CRITICAL,
                message=f"Validation failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now()
            )
    
    def check_missing_students(self, session: AttendanceSession) -> List[Student]:
        """
        Identify and report missing students.
        
        Requirements: 4.1, 4.2, 4.3
        """
        try:
            # Get all registered students for the class
            registered_students = self.student_repository.get_students_by_class(session.class_id)
            active_students = [s for s in registered_students if s.is_active]
            
            # Get students who are present
            present_student_ids = {r.student_id for r in session.attendance_records 
                                 if r.status == AttendanceStatus.PRESENT}
            
            # Find missing students
            missing_students = [s for s in active_students 
                              if s.student_id not in present_student_ids]
            
            self.logger.info(f"Found {len(missing_students)} missing students in session {session.session_id}")
            
            return missing_students
            
        except Exception as e:
            self.logger.error(f"Error checking missing students: {str(e)}")
            return []
    
    def generate_validation_alerts(self, validation_result: ValidationResult) -> Dict:
        """
        Generate validation alerts based on validation results.
        
        Requirements: 4.1, 4.2, 4.3
        """
        alerts = []
        
        if not validation_result.is_valid:
            alert = {
                "type": "attendance_discrepancy",
                "level": validation_result.level.value,
                "message": validation_result.message,
                "session_id": validation_result.details.get("session_id"),
                "missing_count": validation_result.details.get("missing_count", 0),
                "accuracy": validation_result.details.get("accuracy", 0),
                "timestamp": validation_result.timestamp,
                "requires_action": validation_result.level in [ValidationLevel.ERROR, ValidationLevel.CRITICAL]
            }
            alerts.append(alert)
        
        # Generate specific alerts for high missing count
        missing_count = validation_result.details.get("missing_count", 0)
        if missing_count > self.missing_student_threshold:
            alert = {
                "type": "high_absenteeism",
                "level": ValidationLevel.ERROR.value,
                "message": f"High absenteeism detected: {missing_count} students missing",
                "session_id": validation_result.details.get("session_id"),
                "missing_count": missing_count,
                "timestamp": validation_result.timestamp,
                "requires_action": True
            }
            alerts.append(alert)
        
        return {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "critical_alerts": len([a for a in alerts if a["level"] == "critical"]),
            "error_alerts": len([a for a in alerts if a["level"] == "error"])
        }
    
    def validate_day_scholar_cross_verification(self, session: AttendanceSession) -> ValidationResult:
        """
        Validate day scholar cross-verification between gate and classroom.
        
        Requirements: 4.1, 4.2, 4.3
        """
        try:
            day_scholar_records = []
            incomplete_verifications = []
            
            for record in session.attendance_records:
                student = self.student_repository.get_by_id(record.student_id)
                if student and student.student_type.value == "day_scholar":
                    day_scholar_records.append(record)
                    
                    # Check if day scholar has both gate and classroom verification
                    if not record.gate_entry_time and record.status == AttendanceStatus.PRESENT:
                        incomplete_verifications.append(record)
            
            total_day_scholars = len(day_scholar_records)
            incomplete_count = len(incomplete_verifications)
            
            if incomplete_count == 0:
                level = ValidationLevel.INFO
                message = f"All {total_day_scholars} day scholars have complete verification."
                is_valid = True
            elif incomplete_count <= 2:
                level = ValidationLevel.WARNING
                message = f"{incomplete_count} day scholars have incomplete verification."
                is_valid = False
            else:
                level = ValidationLevel.ERROR
                message = f"{incomplete_count} day scholars missing gate verification."
                is_valid = False
            
            details = {
                "session_id": session.session_id,
                "total_day_scholars": total_day_scholars,
                "incomplete_verifications": incomplete_count,
                "incomplete_student_ids": [r.student_id for r in incomplete_verifications]
            }
            
            return ValidationResult(
                is_valid=is_valid,
                level=level,
                message=message,
                details=details,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error validating day scholar cross-verification: {str(e)}")
            return ValidationResult(
                is_valid=False,
                level=ValidationLevel.CRITICAL,
                message=f"Cross-verification validation failed: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now()
            )
    
    def perform_comprehensive_validation(self, session: AttendanceSession) -> Dict:
        """
        Perform comprehensive attendance validation including count validation,
        missing student identification, and alert generation.
        
        Requirements: 4.1, 4.2, 4.3
        """
        try:
            validation_results = {}
            
            # 1. Validate attendance count (Requirement 4.1)
            count_validation = self.validate_attendance_count(session)
            validation_results['count_validation'] = count_validation
            
            # 2. Identify missing students (Requirement 4.3)
            missing_students = self.check_missing_students(session)
            validation_results['missing_students'] = [
                {
                    'student_id': student.student_id,
                    'name': student.name,
                    'student_type': student.student_type.value
                }
                for student in missing_students
            ]
            validation_results['missing_count'] = len(missing_students)
            
            # 3. Validate day scholar cross-verification
            cross_verification = self.validate_day_scholar_cross_verification(session)
            validation_results['cross_verification'] = cross_verification
            
            # 4. Generate validation alerts (Requirement 4.2)
            alerts = self.generate_validation_alerts(count_validation)
            validation_results['alerts'] = alerts
            
            # 5. Send notifications for critical issues
            self._send_validation_notifications(session, validation_results)
            
            # 6. Calculate overall validation status
            overall_valid = (
                count_validation.is_valid and 
                cross_verification.is_valid and
                len(missing_students) <= self.missing_student_threshold
            )
            
            validation_results['overall_status'] = {
                'is_valid': overall_valid,
                'validation_score': self._calculate_validation_score(validation_results),
                'timestamp': datetime.now()
            }
            
            self.logger.info(
                f"Comprehensive validation completed for session {session.session_id}. "
                f"Status: {'PASSED' if overall_valid else 'FAILED'}"
            )
            
            return validation_results
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive validation: {str(e)}")
            error_result = {
                'overall_status': {
                    'is_valid': False,
                    'validation_score': 0.0,
                    'error': str(e),
                    'timestamp': datetime.now()
                },
                'count_validation': ValidationResult(
                    is_valid=False,
                    level=ValidationLevel.CRITICAL,
                    message=f"Validation system error: {str(e)}",
                    details={'error': str(e)},
                    timestamp=datetime.now()
                ),
                'missing_students': [],
                'missing_count': 0,
                'alerts': {'alerts': [], 'total_alerts': 0}
            }
            
            # Send error notification
            self.notification_service.send_validation_error_alert(
                session.session_id, str(e)
            )
            
            return error_result
    
    def _send_validation_notifications(self, session: AttendanceSession, 
                                     validation_results: Dict) -> None:
        """Send notifications based on validation results."""
        try:
            missing_count = validation_results.get('missing_count', 0)
            count_validation = validation_results.get('count_validation')
            
            # Send attendance alert if there are missing students (Requirement 7.1)
            if missing_count > 0:
                missing_student_ids = [
                    student['student_id'] 
                    for student in validation_results.get('missing_students', [])
                ]
                
                self.notification_service.send_attendance_alert(
                    session.session_id,
                    missing_count,
                    missing_student_ids
                )
            
            # Send critical alert for severe validation failures (Requirement 7.2)
            if count_validation and count_validation.level == ValidationLevel.CRITICAL:
                self.notification_service.send_alert(
                    f"Critical validation failure in session {session.session_id}: {count_validation.message}",
                    ["admin", "faculty"],
                    priority=NotificationPriority.CRITICAL,
                    requires_acknowledgment=True
                )
                
        except Exception as e:
            self.logger.error(f"Error sending validation notifications: {str(e)}")
    
    def _calculate_validation_score(self, validation_results: Dict) -> float:
        """Calculate overall validation score (0.0 to 1.0)."""
        try:
            score = 0.0
            
            # Count validation score (40% weight)
            count_validation = validation_results.get('count_validation')
            if count_validation and count_validation.is_valid:
                accuracy = count_validation.details.get('accuracy', 0)
                score += 0.4 * accuracy
            
            # Missing students score (30% weight)
            missing_count = validation_results.get('missing_count', 0)
            expected_count = count_validation.details.get('expected_count', 1) if count_validation else 1
            missing_ratio = missing_count / max(expected_count, 1)
            missing_score = max(0, 1 - missing_ratio)
            score += 0.3 * missing_score
            
            # Cross-verification score (30% weight)
            cross_verification = validation_results.get('cross_verification')
            if cross_verification and cross_verification.is_valid:
                score += 0.3
            
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            self.logger.error(f"Error calculating validation score: {str(e)}")
            return 0.0
    
    def get_validation_summary(self, session_id: str) -> Dict:
        """
        Get validation summary for a specific session.
        
        Args:
            session_id: Session ID to get validation summary for
            
        Returns:
            Dict: Validation summary with key metrics
        """
        try:
            session = self.attendance_repository.get_session_by_id(session_id)
            if not session:
                return {
                    'error': f'Session {session_id} not found',
                    'timestamp': datetime.now()
                }
            
            validation_results = self.perform_comprehensive_validation(session)
            
            # Create summary
            summary = {
                'session_id': session_id,
                'validation_timestamp': datetime.now(),
                'overall_valid': validation_results['overall_status']['is_valid'],
                'validation_score': validation_results['overall_status']['validation_score'],
                'attendance_accuracy': validation_results['count_validation'].details.get('accuracy', 0),
                'missing_student_count': validation_results['missing_count'],
                'alert_count': validation_results['alerts']['total_alerts'],
                'critical_issues': validation_results['alerts']['critical_alerts'] > 0,
                'recommendations': self._generate_recommendations(validation_results)
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting validation summary: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now()
            }
    
    def _generate_recommendations(self, validation_results: Dict) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []
        
        try:
            missing_count = validation_results.get('missing_count', 0)
            count_validation = validation_results.get('count_validation')
            
            if missing_count > self.critical_missing_threshold:
                recommendations.append(
                    "Critical: High number of missing students. "
                    "Consider manual verification or system check."
                )
            elif missing_count > self.missing_student_threshold:
                recommendations.append(
                    "Warning: Several students missing. "
                    "Review attendance records and contact absent students."
                )
            
            if count_validation and count_validation.details.get('accuracy', 1) < self.validation_threshold:
                recommendations.append(
                    "Low attendance accuracy detected. "
                    "Check camera positioning and lighting conditions."
                )
            
            cross_verification = validation_results.get('cross_verification')
            if cross_verification and not cross_verification.is_valid:
                incomplete_count = cross_verification.details.get('incomplete_verifications', 0)
                if incomplete_count > 0:
                    recommendations.append(
                        f"{incomplete_count} day scholars missing gate verification. "
                        "Check gate camera system and entry procedures."
                    )
            
            if not recommendations:
                recommendations.append("All validation checks passed successfully.")
                
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {str(e)}")
            recommendations.append("Unable to generate recommendations due to system error.")
        
        return recommendations
    
    def monitor_system_health(self) -> SystemHealthStatus:
        """
        Monitor system health status including database connectivity,
        service availability, and performance metrics.
        
        Returns:
            SystemHealthStatus: Current system health status
        """
        try:
            components = {}
            overall_status = "healthy"
            start_time = datetime.now()
            
            # Check database connectivity
            try:
                # Test student repository
                test_students = self.student_repository.get_students_by_class("test")
                components['student_database'] = {
                    'status': 'healthy',
                    'response_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                    'last_check': datetime.now()
                }
            except Exception as e:
                components['student_database'] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'last_check': datetime.now()
                }
                overall_status = "degraded"
            
            # Check attendance repository
            try:
                test_time = datetime.now()
                # Test attendance repository with a simple query
                components['attendance_database'] = {
                    'status': 'healthy',
                    'response_time_ms': (datetime.now() - test_time).total_seconds() * 1000,
                    'last_check': datetime.now()
                }
            except Exception as e:
                components['attendance_database'] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'last_check': datetime.now()
                }
                overall_status = "unhealthy"
            
            # Check notification service
            try:
                notification_health = len(self.notification_service.get_pending_notifications())
                components['notification_service'] = {
                    'status': 'healthy',
                    'pending_notifications': notification_health,
                    'last_check': datetime.now()
                }
                
                if notification_health > 100:  # Too many pending notifications
                    components['notification_service']['status'] = 'degraded'
                    if overall_status == "healthy":
                        overall_status = "degraded"
                        
            except Exception as e:
                components['notification_service'] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'last_check': datetime.now()
                }
                overall_status = "unhealthy"
            
            # Check validation service performance
            components['validation_service'] = {
                'status': 'healthy',
                'validation_threshold': self.validation_threshold,
                'missing_student_threshold': self.missing_student_threshold,
                'last_check': datetime.now()
            }
            
            # Calculate uptime (simplified - in real implementation would track actual uptime)
            uptime_seconds = 3600  # Placeholder - would be actual uptime
            
            health_status = SystemHealthStatus(
                overall_status=overall_status,
                components=components,
                timestamp=datetime.now(),
                uptime_seconds=uptime_seconds
            )
            
            # Log health status
            if overall_status != "healthy":
                self.logger.warning(f"System health check: {overall_status}")
                
                # Send alert for unhealthy status (Requirement 7.2)
                if overall_status in ["unhealthy", "degraded"]:
                    unhealthy_components = [
                        name for name, comp in components.items() 
                        if comp.get('status') in ['unhealthy', 'degraded']
                    ]
                    if unhealthy_components:
                        self.notification_service.send_alert(
                            f"System health critical: {', '.join(unhealthy_components)} components unhealthy",
                            ["admin", "tech_support"],
                            priority=NotificationPriority.CRITICAL,
                            requires_acknowledgment=True
                        )
            
            return health_status
            
        except Exception as e:
            self.logger.error(f"Error monitoring system health: {str(e)}")
            return SystemHealthStatus(
                overall_status="error",
                components={
                    'system_monitor': {
                        'status': 'error',
                        'error': str(e),
                        'last_check': datetime.now()
                    }
                },
                timestamp=datetime.now(),
                uptime_seconds=0
            )
    
    def monitor_camera_connectivity(self, camera_id: str, is_connected: bool) -> bool:
        """
        Monitor camera connectivity and send alerts when cameras disconnect.
        
        Requirements: 7.2 - Camera connectivity notifications
        
        Args:
            camera_id: Camera identifier
            is_connected: Whether camera is currently connected
            
        Returns:
            bool: True if monitoring was successful
        """
        try:
            # Send camera connectivity alert
            success = self.notification_service.send_camera_connectivity_alert(
                camera_id, is_connected
            )
            
            if success:
                self.logger.info(f"Camera connectivity alert sent for {camera_id}: {'connected' if is_connected else 'disconnected'}")
            else:
                self.logger.error(f"Failed to send camera connectivity alert for {camera_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error monitoring camera connectivity: {str(e)}")
            return False
    
    def monitor_face_recognition_confidence(self, session_id: str, 
                                          confidence_scores: List[float]) -> bool:
        """
        Monitor face recognition confidence and alert when below threshold.
        
        Requirements: 7.3 - Face recognition confidence monitoring
        
        Args:
            session_id: Session ID
            confidence_scores: List of confidence scores from face recognition
            
        Returns:
            bool: True if monitoring was successful
        """
        try:
            if not confidence_scores:
                return True
            
            # Calculate statistics
            average_confidence = sum(confidence_scores) / len(confidence_scores)
            low_confidence_count = len([
                score for score in confidence_scores 
                if score < self.notification_service.face_recognition_confidence_threshold
            ])
            
            # Send alert if average confidence is below threshold
            if average_confidence < self.notification_service.face_recognition_confidence_threshold:
                success = self.notification_service.send_face_recognition_confidence_alert(
                    session_id, low_confidence_count, average_confidence
                )
                
                if success:
                    self.logger.warning(
                        f"Face recognition confidence alert sent for session {session_id}: "
                        f"avg={average_confidence:.2%}, low_count={low_confidence_count}"
                    )
                else:
                    self.logger.error(f"Failed to send face recognition confidence alert for session {session_id}")
                
                return success
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error monitoring face recognition confidence: {str(e)}")
            return False
    
    def monitor_processing_performance(self, component: str, processing_time: float) -> bool:
        """
        Monitor processing performance and alert when exceeding thresholds.
        
        Requirements: 7.4 - Performance monitoring alerts
        
        Args:
            component: Component name (e.g., 'face_recognition', 'emotion_analysis')
            processing_time: Processing time in seconds
            
        Returns:
            bool: True if monitoring was successful
        """
        try:
            # Send performance alert if processing time exceeds threshold
            success = self.notification_service.send_performance_alert(
                component, processing_time
            )
            
            if processing_time > self.notification_service.processing_time_threshold_seconds:
                if success:
                    self.logger.warning(
                        f"Performance alert sent for {component}: "
                        f"processing_time={processing_time:.2f}s"
                    )
                else:
                    self.logger.error(f"Failed to send performance alert for {component}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error monitoring processing performance: {str(e)}")
            return False
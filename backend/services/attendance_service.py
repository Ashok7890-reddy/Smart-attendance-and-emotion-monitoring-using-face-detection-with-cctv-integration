"""
Attendance management service implementation.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4
import asyncio

from ..core.interfaces import IAttendanceService, IFaceRecognitionService
from ..models.student import Student, StudentType, StudentMatch
from ..models.attendance import AttendanceSession, AttendanceRecord, AttendanceStatus
from ..models.face_detection import FaceDetection, CameraLocation
from ..database.repositories import AttendanceRepository, StudentRepository, FaceDetectionRepository
from ..core.cache import get_redis_client
from ..core.config import get_settings
from .websocket_integration_service import get_websocket_integration

logger = logging.getLogger(__name__)


class AttendanceService(IAttendanceService):
    """Attendance management service implementation."""
    
    def __init__(self, 
                 attendance_repo: AttendanceRepository,
                 student_repo: StudentRepository,
                 face_detection_repo: FaceDetectionRepository,
                 face_recognition_service: IFaceRecognitionService):
        self.attendance_repo = attendance_repo
        self.student_repo = student_repo
        self.face_detection_repo = face_detection_repo
        self.face_recognition_service = face_recognition_service
        self.redis = get_redis_client()
        self.settings = get_settings()
        self.websocket_integration = get_websocket_integration()
        
        # Cache keys
        self.GATE_ENTRY_KEY = "gate_entry:{student_id}:{date}"
        self.DUPLICATE_DETECTION_KEY = "duplicate_gate:{student_id}:{timestamp}"
        
    async def record_gate_entry(self, student_id: str, timestamp: datetime) -> bool:
        """
        Record gate entry for a day scholar.
        
        Requirements: 2.1, 2.2
        - Create gate camera integration and face recognition workflow
        - Implement gate entry logging with timestamp and student identification
        - Set up gate entry validation and duplicate detection
        """
        try:
            # Validate student exists and is a day scholar
            student = await self.student_repo.get_student_by_id(student_id)
            if not student:
                logger.warning(f"Gate entry attempted for non-existent student: {student_id}")
                return False
                
            if student.student_type != StudentType.DAY_SCHOLAR:
                logger.warning(f"Gate entry attempted for non-day scholar: {student_id}")
                return False
            
            if not student.is_active:
                logger.warning(f"Gate entry attempted for inactive student: {student_id}")
                return False
            
            # Check for duplicate entries within a short time window (5 minutes)
            duplicate_key = self.DUPLICATE_DETECTION_KEY.format(
                student_id=student_id,
                timestamp=int(timestamp.timestamp() // 300)  # 5-minute buckets
            )
            
            if await self.redis.exists(duplicate_key):
                logger.info(f"Duplicate gate entry detected for student {student_id}, ignoring")
                return True  # Return True as entry was already recorded
            
            # Record gate entry in cache for quick access
            date_str = timestamp.strftime("%Y-%m-%d")
            gate_entry_key = self.GATE_ENTRY_KEY.format(
                student_id=student_id,
                date=date_str
            )
            
            # Store gate entry with expiration (24 hours)
            gate_entry_data = {
                'student_id': student_id,
                'timestamp': timestamp.isoformat(),
                'date': date_str
            }
            
            await self.redis.setex(
                gate_entry_key,
                86400,  # 24 hours
                str(gate_entry_data)
            )
            
            # Set duplicate detection flag (5 minutes)
            await self.redis.setex(duplicate_key, 300, "1")
            
            logger.info(f"Gate entry recorded for day scholar: {student_id} at {timestamp}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to record gate entry for {student_id}: {e}")
            return False
    
    async def get_gate_entry(self, student_id: str, date: datetime) -> Optional[Dict[str, Any]]:
        """Get gate entry record for a student on a specific date."""
        try:
            date_str = date.strftime("%Y-%m-%d")
            gate_entry_key = self.GATE_ENTRY_KEY.format(
                student_id=student_id,
                date=date_str
            )
            
            entry_data = await self.redis.get(gate_entry_key)
            if entry_data:
                # Parse the stored data (simplified for this implementation)
                return {
                    'student_id': student_id,
                    'timestamp': entry_data,
                    'date': date_str
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get gate entry for {student_id}: {e}")
            return None
    
    async def validate_gate_entry(self, student_id: str, timestamp: datetime) -> bool:
        """Validate if a day scholar has a valid gate entry for the day."""
        try:
            gate_entry = await self.get_gate_entry(student_id, timestamp)
            if not gate_entry:
                return False
            
            # Parse gate entry timestamp
            gate_time = datetime.fromisoformat(gate_entry['timestamp'].strip('"\''))
            
            # Validate gate entry is within reasonable time window (same day, before classroom entry)
            if (gate_time.date() == timestamp.date() and 
                gate_time <= timestamp and 
                (timestamp - gate_time).total_seconds() <= 43200):  # 12 hours max
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to validate gate entry for {student_id}: {e}")
            return False
    
    async def process_gate_camera_frame(self, frame, camera_id: str) -> List[str]:
        """
        Process a frame from gate camera for face recognition.
        
        Returns list of student IDs detected and processed.
        """
        try:
            # Detect faces in the frame
            detections = self.face_recognition_service.detect_faces(frame)
            
            processed_students = []
            current_time = datetime.utcnow()
            
            for detection in detections:
                # Verify liveness to prevent spoofing
                if detection.liveness_score < self.settings.LIVENESS_THRESHOLD:
                    logger.warning(f"Low liveness score detected at gate: {detection.liveness_score}")
                    continue
                
                # Match face against enrolled students
                student_match = self.face_recognition_service.match_face(detection.embedding)
                
                if student_match and student_match.confidence >= self.settings.FACE_MATCH_THRESHOLD:
                    # Record gate entry
                    success = await self.record_gate_entry(
                        student_match.student.student_id,
                        current_time
                    )
                    
                    if success:
                        processed_students.append(student_match.student.student_id)
                        
                        # Store face detection record
                        detection.student_id = student_match.student.student_id
                        detection.camera_location = CameraLocation.GATE
                        await self.face_detection_repo.create_detection(detection)
            
            return processed_students
            
        except Exception as e:
            logger.error(f"Failed to process gate camera frame: {e}")
            return []
    
    async def mark_classroom_attendance(self, detections: List[FaceDetection]) -> AttendanceSession:
        """
        Mark classroom attendance based on face detections.
        
        Requirements: 1.2, 1.3, 2.4
        - Create classroom camera integration for all students
        - Implement real-time face detection and identification in classroom
        - Set up attendance marking with location and timestamp data
        """
        try:
            if not detections:
                logger.warning("No face detections provided for classroom attendance")
                return None
            
            # Create new attendance session
            session_id = str(uuid4())
            current_time = datetime.utcnow()
            
            # Get class information from first detection (assuming all from same class)
            # In real implementation, this would be passed as parameter
            class_id = "default_class"  # Placeholder
            faculty_id = "default_faculty"  # Placeholder
            
            # Get registered students for the class
            registered_students = await self.student_repo.get_students_by_class(class_id)
            total_registered = len(registered_students)
            
            # Create attendance session
            session = AttendanceSession(
                session_id=session_id,
                class_id=class_id,
                faculty_id=faculty_id,
                start_time=current_time,
                total_registered=total_registered,
                total_detected=0,
                attendance_records=[],
                is_active=True
            )
            
            # Store session in database
            await self.attendance_repo.create_session(session)
            
            # Process each face detection
            detected_students = set()
            attendance_records = []
            
            for detection in detections:
                try:
                    # Verify liveness
                    if detection.liveness_score < self.settings.LIVENESS_THRESHOLD:
                        logger.warning(f"Low liveness score in classroom: {detection.liveness_score}")
                        continue
                    
                    # Match face against enrolled students
                    student_match = self.face_recognition_service.match_face(detection.embedding)
                    
                    if student_match and student_match.confidence >= self.settings.FACE_MATCH_THRESHOLD:
                        student_id = student_match.student.student_id
                        
                        # Avoid duplicate attendance for same student
                        if student_id in detected_students:
                            continue
                        
                        detected_students.add(student_id)
                        
                        # Create attendance record
                        record = AttendanceRecord(
                            student_id=student_id,
                            session_id=session_id,
                            status=AttendanceStatus.PRESENT,
                            timestamp=current_time,
                            confidence=student_match.confidence,
                            classroom_entry_time=current_time
                        )
                        
                        # Store attendance record
                        await self.attendance_repo.create_attendance_record(record)
                        attendance_records.append(record)
                        
                        # Store face detection record
                        detection.student_id = student_id
                        detection.camera_location = CameraLocation.CLASSROOM
                        await self.face_detection_repo.create_detection(detection)
                        
                        logger.debug(f"Classroom attendance marked: {student_id}")
                    
                except Exception as e:
                    logger.error(f"Error processing detection: {e}")
                    continue
            
            # Update session with detection count
            total_detected = len(detected_students)
            await self.attendance_repo.update_session_counts(session_id, total_detected)
            
            # Update session object
            session.total_detected = total_detected
            session.attendance_records = attendance_records
            
            # Broadcast real-time attendance update via WebSocket
            try:
                await self.websocket_integration.broadcast_attendance_update(session)
            except Exception as ws_error:
                logger.warning(f"Failed to broadcast attendance update: {ws_error}")
            
            logger.info(f"Classroom attendance processed: {total_detected}/{total_registered} students detected")
            return session
            
        except Exception as e:
            logger.error(f"Failed to mark classroom attendance: {e}")
            raise
    
    async def validate_day_scholar_attendance(self, student_id: str, session_id: str) -> bool:
        """
        Validate day scholar attendance with cross-verification.
        
        Requirements: 2.2, 2.3, 2.5
        - Create cross-verification workflow matching gate and classroom records
        - Implement day scholar attendance validation requiring both verifications
        - Set up incomplete attendance flagging and alerts
        """
        try:
            # Get student information
            student = await self.student_repo.get_student_by_id(student_id)
            if not student:
                logger.warning(f"Cross-verification attempted for non-existent student: {student_id}")
                return False
            
            # Only validate day scholars
            if student.student_type != StudentType.DAY_SCHOLAR:
                logger.debug(f"Cross-verification skipped for non-day scholar: {student_id}")
                return True  # Hostel students don't need gate verification
            
            # Get session information
            session = await self.attendance_repo.get_session_by_id(session_id)
            if not session:
                logger.warning(f"Cross-verification attempted for non-existent session: {session_id}")
                return False
            
            # Check if student has gate entry for the session date
            has_gate_entry = await self.validate_gate_entry(student_id, session.start_time)
            
            if not has_gate_entry:
                # Mark attendance as incomplete
                await self._mark_attendance_incomplete(student_id, session_id, "Missing gate entry")
                logger.warning(f"Day scholar {student_id} has no gate entry for session {session_id}")
                return False
            
            # Get classroom attendance record
            attendance_records = await self.attendance_repo.get_session_attendance(session_id)
            classroom_record = next((r for r in attendance_records if r.student_id == student_id), None)
            
            if not classroom_record:
                logger.warning(f"No classroom record found for day scholar {student_id} in session {session_id}")
                return False
            
            # Validate timing - gate entry should be before classroom entry
            gate_entry = await self.get_gate_entry(student_id, session.start_time)
            if gate_entry:
                gate_time = datetime.fromisoformat(gate_entry['timestamp'].strip('"\''))
                classroom_time = classroom_record.classroom_entry_time
                
                if gate_time > classroom_time:
                    await self._mark_attendance_incomplete(student_id, session_id, "Gate entry after classroom entry")
                    logger.warning(f"Invalid timing for day scholar {student_id}: gate after classroom")
                    return False
            
            # Update attendance record with gate entry time
            if classroom_record.gate_entry_time is None:
                gate_entry_time = datetime.fromisoformat(gate_entry['timestamp'].strip('"\''))
                await self._update_attendance_with_gate_time(student_id, session_id, gate_entry_time)
            
            logger.info(f"Cross-verification successful for day scholar: {student_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate day scholar attendance for {student_id}: {e}")
            return False
    
    async def _mark_attendance_incomplete(self, student_id: str, session_id: str, reason: str):
        """Mark attendance as incomplete with reason."""
        try:
            # Get existing attendance record
            attendance_records = await self.attendance_repo.get_session_attendance(session_id)
            existing_record = next((r for r in attendance_records if r.student_id == student_id), None)
            
            if existing_record:
                # Update existing record to incomplete
                await self.attendance_repo.update_attendance_record(
                    existing_record.id,
                    {
                        'status': AttendanceStatus.INCOMPLETE,
                        'notes': reason
                    }
                )
            else:
                # Create new incomplete record
                record = AttendanceRecord(
                    student_id=student_id,
                    session_id=session_id,
                    status=AttendanceStatus.INCOMPLETE,
                    timestamp=datetime.utcnow(),
                    confidence=0.0
                )
                await self.attendance_repo.create_attendance_record(record)
            
            logger.info(f"Attendance marked incomplete for {student_id}: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to mark attendance incomplete for {student_id}: {e}")
    
    async def _update_attendance_with_gate_time(self, student_id: str, session_id: str, gate_time: datetime):
        """Update attendance record with gate entry time."""
        try:
            attendance_records = await self.attendance_repo.get_session_attendance(session_id)
            record = next((r for r in attendance_records if r.student_id == student_id), None)
            
            if record:
                await self.attendance_repo.update_attendance_record(
                    record.id,
                    {'gate_entry_time': gate_time}
                )
                logger.debug(f"Updated gate entry time for {student_id}")
            
        except Exception as e:
            logger.error(f"Failed to update gate entry time for {student_id}: {e}")
    
    async def generate_attendance_report(self, session_id: str) -> dict:
        """Generate comprehensive attendance report for a session."""
        try:
            # Get session information
            session = await self.attendance_repo.get_session_by_id(session_id)
            if not session:
                return {'error': 'Session not found'}
            
            # Get all attendance records
            attendance_records = await self.attendance_repo.get_session_attendance(session_id)
            
            # Get all students in the class
            all_students = await self.student_repo.get_students_by_class(session.class_id)
            
            # Separate day scholars and hostel students
            day_scholars = [s for s in all_students if s.student_type == StudentType.DAY_SCHOLAR]
            hostel_students = [s for s in all_students if s.student_type == StudentType.HOSTEL_STUDENT]
            
            # Process day scholar attendance with cross-verification
            cross_verifier = CrossVerificationProcessor(self)
            day_scholar_results = await cross_verifier.run_cross_verification(session_id)
            
            # Process hostel student attendance
            hostel_processor = HostelStudentProcessor(self)
            hostel_results = await hostel_processor.validate_hostel_attendance(session_id)
            
            # Generate comprehensive report
            report = {
                'session_info': {
                    'session_id': session_id,
                    'class_id': session.class_id,
                    'faculty_id': session.faculty_id,
                    'start_time': session.start_time.isoformat(),
                    'end_time': session.end_time.isoformat() if session.end_time else None,
                    'is_active': session.is_active
                },
                'overall_statistics': {
                    'total_registered': len(all_students),
                    'total_day_scholars': len(day_scholars),
                    'total_hostel_students': len(hostel_students),
                    'total_present': len([r for r in attendance_records if r.status == AttendanceStatus.PRESENT]),
                    'total_absent': len([r for r in attendance_records if r.status == AttendanceStatus.ABSENT]),
                    'total_incomplete': len([r for r in attendance_records if r.status == AttendanceStatus.INCOMPLETE]),
                    'overall_attendance_rate': 0.0
                },
                'day_scholar_report': day_scholar_results,
                'hostel_student_report': hostel_results,
                'alerts': [],
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Calculate overall attendance rate
            total_present = report['overall_statistics']['total_present']
            total_registered = report['overall_statistics']['total_registered']
            if total_registered > 0:
                report['overall_statistics']['overall_attendance_rate'] = round(
                    (total_present / total_registered) * 100, 2
                )
            
            # Collect alerts
            if 'alerts' in day_scholar_results:
                report['alerts'].extend(day_scholar_results['alerts'])
            
            # Add general alerts
            if report['overall_statistics']['total_incomplete'] > 0:
                report['alerts'].append(
                    f"{report['overall_statistics']['total_incomplete']} students have incomplete attendance"
                )
            
            logger.info(f"Attendance report generated for session {session_id}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate attendance report for session {session_id}: {e}")
            return {'error': str(e)}


class GateEntryTracker:
    """Specialized class for gate entry tracking operations."""
    
    def __init__(self, attendance_service: AttendanceService):
        self.attendance_service = attendance_service
        self.logger = logging.getLogger(f"{__name__}.GateEntryTracker")
    
    async def start_gate_monitoring(self, camera_id: str):
        """Start continuous monitoring of gate camera."""
        self.logger.info(f"Starting gate monitoring for camera: {camera_id}")
        
        # This would integrate with actual camera service
        # For now, this is a placeholder for the monitoring loop
        while True:
            try:
                # In real implementation, this would get frame from camera service
                # frame = await camera_service.get_frame(camera_id)
                # processed = await self.attendance_service.process_gate_camera_frame(frame, camera_id)
                
                await asyncio.sleep(0.1)  # Process at ~10 FPS
                
            except Exception as e:
                self.logger.error(f"Error in gate monitoring: {e}")
                await asyncio.sleep(1)  # Brief pause on error
    
    async def get_daily_gate_entries(self, date: datetime) -> List[Dict[str, Any]]:
        """Get all gate entries for a specific date."""
        try:
            # This would query Redis for all gate entries on the date
            # Implementation depends on Redis key pattern matching
            entries = []
            
            # Placeholder - in real implementation would scan Redis keys
            # pattern = f"gate_entry:*:{date.strftime('%Y-%m-%d')}"
            # keys = await self.attendance_service.redis.keys(pattern)
            
            return entries
            
        except Exception as e:
            self.logger.error(f"Failed to get daily gate entries for {date}: {e}")
            return []
    
    async def validate_gate_entry_integrity(self, student_id: str, date: datetime) -> bool:
        """Validate integrity of gate entry record."""
        try:
            gate_entry = await self.attendance_service.get_gate_entry(student_id, date)
            if not gate_entry:
                return False
            
            # Additional validation logic
            # - Check timestamp format
            # - Validate student exists
            # - Check for suspicious patterns
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate gate entry integrity: {e}")
            return False

class ClassroomAttendanceProcessor:
    """Specialized class for classroom attendance processing."""
    
    def __init__(self, attendance_service: AttendanceService):
        self.attendance_service = attendance_service
        self.logger = logging.getLogger(f"{__name__}.ClassroomAttendanceProcessor")
    
    async def start_classroom_session(self, class_id: str, faculty_id: str) -> str:
        """Start a new classroom attendance session."""
        try:
            session_id = str(uuid4())
            current_time = datetime.utcnow()
            
            # Get registered students for the class
            registered_students = await self.attendance_service.student_repo.get_students_by_class(class_id)
            total_registered = len(registered_students)
            
            # Create attendance session
            session = AttendanceSession(
                session_id=session_id,
                class_id=class_id,
                faculty_id=faculty_id,
                start_time=current_time,
                total_registered=total_registered,
                total_detected=0,
                attendance_records=[],
                is_active=True
            )
            
            # Store session in database
            await self.attendance_service.attendance_repo.create_session(session)
            
            self.logger.info(f"Classroom session started: {session_id} for class {class_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Failed to start classroom session: {e}")
            raise
    
    async def process_classroom_frame(self, frame, session_id: str, camera_id: str) -> List[str]:
        """
        Process a frame from classroom camera for attendance.
        
        Returns list of student IDs detected and processed.
        """
        try:
            # Detect faces in the frame
            detections = self.attendance_service.face_recognition_service.detect_faces(frame)
            
            if not detections:
                return []
            
            # Get session to validate it's active
            session = await self.attendance_service.attendance_repo.get_session_by_id(session_id)
            if not session or not session.is_active:
                self.logger.warning(f"Attempted to process frame for inactive session: {session_id}")
                return []
            
            processed_students = []
            current_time = datetime.utcnow()
            
            for detection in detections:
                try:
                    # Verify liveness
                    if detection.liveness_score < self.attendance_service.settings.LIVENESS_THRESHOLD:
                        continue
                    
                    # Match face against enrolled students
                    student_match = self.attendance_service.face_recognition_service.match_face(detection.embedding)
                    
                    if student_match and student_match.confidence >= self.attendance_service.settings.FACE_MATCH_THRESHOLD:
                        student_id = student_match.student.student_id
                        
                        # Check if student already marked present in this session
                        existing_records = await self.attendance_service.attendance_repo.get_session_attendance(session_id)
                        already_present = any(r.student_id == student_id and r.status == AttendanceStatus.PRESENT 
                                            for r in existing_records)
                        
                        if not already_present:
                            # Create attendance record
                            record = AttendanceRecord(
                                student_id=student_id,
                                session_id=session_id,
                                status=AttendanceStatus.PRESENT,
                                timestamp=current_time,
                                confidence=student_match.confidence,
                                classroom_entry_time=current_time
                            )
                            
                            # Store attendance record
                            await self.attendance_service.attendance_repo.create_attendance_record(record)
                            processed_students.append(student_id)
                            
                            # Store face detection record
                            detection.student_id = student_id
                            detection.camera_location = CameraLocation.CLASSROOM
                            await self.attendance_service.face_detection_repo.create_detection(detection)
                            
                            self.logger.debug(f"Student detected in classroom: {student_id}")
                
                except Exception as e:
                    self.logger.error(f"Error processing classroom detection: {e}")
                    continue
            
            # Update session detection count if any new students detected
            if processed_students:
                all_records = await self.attendance_service.attendance_repo.get_session_attendance(session_id)
                total_detected = len([r for r in all_records if r.status == AttendanceStatus.PRESENT])
                await self.attendance_service.attendance_repo.update_session_counts(session_id, total_detected)
            
            return processed_students
            
        except Exception as e:
            self.logger.error(f"Failed to process classroom frame: {e}")
            return []
    
    async def end_classroom_session(self, session_id: str) -> bool:
        """End a classroom attendance session."""
        try:
            success = await self.attendance_service.attendance_repo.end_session(session_id)
            
            if success:
                self.logger.info(f"Classroom session ended: {session_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to end classroom session {session_id}: {e}")
            return False
    
    async def get_real_time_attendance(self, session_id: str) -> Dict[str, Any]:
        """Get real-time attendance data for a session."""
        try:
            session = await self.attendance_service.attendance_repo.get_session_by_id(session_id)
            if not session:
                return {}
            
            attendance_records = await self.attendance_service.attendance_repo.get_session_attendance(session_id)
            
            present_students = [r for r in attendance_records if r.status == AttendanceStatus.PRESENT]
            absent_students = []
            
            # Get all registered students for the class
            registered_students = await self.attendance_service.student_repo.get_students_by_class(session.class_id)
            present_student_ids = {r.student_id for r in present_students}
            
            for student in registered_students:
                if student.student_id not in present_student_ids:
                    absent_students.append({
                        'student_id': student.student_id,
                        'name': student.name,
                        'student_type': student.student_type.value
                    })
            
            return {
                'session_id': session_id,
                'class_id': session.class_id,
                'total_registered': session.total_registered,
                'total_present': len(present_students),
                'total_absent': len(absent_students),
                'attendance_percentage': (len(present_students) / session.total_registered * 100) if session.total_registered > 0 else 0,
                'present_students': [
                    {
                        'student_id': r.student_id,
                        'timestamp': r.timestamp.isoformat(),
                        'confidence': r.confidence
                    } for r in present_students
                ],
                'absent_students': absent_students,
                'session_start': session.start_time.isoformat(),
                'is_active': session.is_active
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get real-time attendance for session {session_id}: {e}")
            return {}
    
    async def start_continuous_monitoring(self, session_id: str, camera_id: str):
        """Start continuous monitoring of classroom camera for a session."""
        self.logger.info(f"Starting classroom monitoring for session: {session_id}")
        
        # This would integrate with actual camera service
        # For now, this is a placeholder for the monitoring loop
        while True:
            try:
                # Check if session is still active
                session = await self.attendance_service.attendance_repo.get_session_by_id(session_id)
                if not session or not session.is_active:
                    self.logger.info(f"Session {session_id} ended, stopping monitoring")
                    break
                
                # In real implementation, this would get frame from camera service
                # frame = await camera_service.get_frame(camera_id)
                # processed = await self.process_classroom_frame(frame, session_id, camera_id)
                
                await asyncio.sleep(1)  # Process at ~1 FPS for attendance
                
            except Exception as e:
                self.logger.error(f"Error in classroom monitoring: {e}")
                await asyncio.sleep(1)  # Brief pause on error


class CrossVerificationProcessor:
    """Specialized class for day scholar cross-verification logic."""
    
    def __init__(self, attendance_service: AttendanceService):
        self.attendance_service = attendance_service
        self.logger = logging.getLogger(f"{__name__}.CrossVerificationProcessor")
    
    async def run_cross_verification(self, session_id: str) -> Dict[str, Any]:
        """
        Run cross-verification for all day scholars in a session.
        
        Returns verification results and alerts.
        """
        try:
            session = await self.attendance_service.attendance_repo.get_session_by_id(session_id)
            if not session:
                return {'error': 'Session not found'}
            
            # Get all attendance records for the session
            attendance_records = await self.attendance_service.attendance_repo.get_session_attendance(session_id)
            
            # Get all day scholars in the class
            all_students = await self.attendance_service.student_repo.get_students_by_class(session.class_id)
            day_scholars = [s for s in all_students if s.student_type == StudentType.DAY_SCHOLAR]
            
            verification_results = {
                'session_id': session_id,
                'total_day_scholars': len(day_scholars),
                'verified_count': 0,
                'incomplete_count': 0,
                'missing_gate_entry': [],
                'timing_violations': [],
                'verified_students': [],
                'alerts': []
            }
            
            for student in day_scholars:
                student_id = student.student_id
                
                # Check if student has classroom attendance
                classroom_record = next((r for r in attendance_records if r.student_id == student_id), None)
                
                if not classroom_record:
                    # Student not detected in classroom
                    continue
                
                # Validate cross-verification
                is_valid = await self.attendance_service.validate_day_scholar_attendance(student_id, session_id)
                
                if is_valid:
                    verification_results['verified_count'] += 1
                    verification_results['verified_students'].append({
                        'student_id': student_id,
                        'name': student.name,
                        'gate_entry_time': classroom_record.gate_entry_time.isoformat() if classroom_record.gate_entry_time else None,
                        'classroom_entry_time': classroom_record.classroom_entry_time.isoformat() if classroom_record.classroom_entry_time else None
                    })
                else:
                    verification_results['incomplete_count'] += 1
                    
                    # Determine the specific issue
                    has_gate_entry = await self.attendance_service.validate_gate_entry(student_id, session.start_time)
                    
                    if not has_gate_entry:
                        verification_results['missing_gate_entry'].append({
                            'student_id': student_id,
                            'name': student.name,
                            'classroom_entry_time': classroom_record.classroom_entry_time.isoformat() if classroom_record.classroom_entry_time else None
                        })
                        verification_results['alerts'].append(f"Day scholar {student.name} ({student_id}) has no gate entry")
                    else:
                        # Check for timing violations
                        gate_entry = await self.attendance_service.get_gate_entry(student_id, session.start_time)
                        if gate_entry:
                            gate_time = datetime.fromisoformat(gate_entry['timestamp'].strip('"\''))
                            classroom_time = classroom_record.classroom_entry_time
                            
                            if gate_time > classroom_time:
                                verification_results['timing_violations'].append({
                                    'student_id': student_id,
                                    'name': student.name,
                                    'gate_time': gate_time.isoformat(),
                                    'classroom_time': classroom_time.isoformat()
                                })
                                verification_results['alerts'].append(f"Day scholar {student.name} ({student_id}) has invalid timing")
            
            self.logger.info(f"Cross-verification completed for session {session_id}: "
                           f"{verification_results['verified_count']}/{verification_results['total_day_scholars']} verified")
            
            return verification_results
            
        except Exception as e:
            self.logger.error(f"Failed to run cross-verification for session {session_id}: {e}")
            return {'error': str(e)}
    
    async def generate_incomplete_attendance_alerts(self, session_id: str) -> List[Dict[str, Any]]:
        """Generate alerts for incomplete day scholar attendance."""
        try:
            verification_results = await self.run_cross_verification(session_id)
            
            alerts = []
            
            # Alert for missing gate entries
            if verification_results.get('missing_gate_entry'):
                alerts.append({
                    'type': 'missing_gate_entry',
                    'severity': 'high',
                    'message': f"{len(verification_results['missing_gate_entry'])} day scholars have no gate entry",
                    'students': verification_results['missing_gate_entry'],
                    'session_id': session_id
                })
            
            # Alert for timing violations
            if verification_results.get('timing_violations'):
                alerts.append({
                    'type': 'timing_violation',
                    'severity': 'medium',
                    'message': f"{len(verification_results['timing_violations'])} day scholars have timing violations",
                    'students': verification_results['timing_violations'],
                    'session_id': session_id
                })
            
            # General incomplete attendance alert
            if verification_results.get('incomplete_count', 0) > 0:
                alerts.append({
                    'type': 'incomplete_attendance',
                    'severity': 'medium',
                    'message': f"{verification_results['incomplete_count']} day scholars have incomplete attendance",
                    'count': verification_results['incomplete_count'],
                    'session_id': session_id
                })
            
            return alerts
            
        except Exception as e:
            self.logger.error(f"Failed to generate incomplete attendance alerts: {e}")
            return []
    
    async def fix_incomplete_attendance(self, student_id: str, session_id: str, manual_gate_time: Optional[datetime] = None) -> bool:
        """
        Manually fix incomplete attendance for a day scholar.
        
        This allows administrators to manually verify and fix attendance issues.
        """
        try:
            student = await self.attendance_service.student_repo.get_student_by_id(student_id)
            if not student or student.student_type != StudentType.DAY_SCHOLAR:
                return False
            
            # Get attendance record
            attendance_records = await self.attendance_service.attendance_repo.get_session_attendance(session_id)
            record = next((r for r in attendance_records if r.student_id == student_id), None)
            
            if not record:
                return False
            
            # Update record with manual gate time if provided
            if manual_gate_time:
                await self.attendance_service.attendance_repo.update_attendance_record(
                    record.id,
                    {
                        'gate_entry_time': manual_gate_time,
                        'status': AttendanceStatus.PRESENT,
                        'notes': 'Manually verified by administrator'
                    }
                )
                
                self.logger.info(f"Manually fixed attendance for day scholar {student_id}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to fix incomplete attendance for {student_id}: {e}")
            return False
    
    async def get_cross_verification_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of cross-verification results for a session."""
        try:
            verification_results = await self.run_cross_verification(session_id)
            
            if 'error' in verification_results:
                return verification_results
            
            total_day_scholars = verification_results['total_day_scholars']
            verified_count = verification_results['verified_count']
            incomplete_count = verification_results['incomplete_count']
            
            verification_rate = (verified_count / total_day_scholars * 100) if total_day_scholars > 0 else 0
            
            return {
                'session_id': session_id,
                'total_day_scholars': total_day_scholars,
                'verified_count': verified_count,
                'incomplete_count': incomplete_count,
                'verification_rate': round(verification_rate, 2),
                'status': 'complete' if incomplete_count == 0 else 'incomplete',
                'alerts_count': len(verification_results.get('alerts', [])),
                'summary': f"{verified_count}/{total_day_scholars} day scholars verified ({verification_rate:.1f}%)"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get cross-verification summary: {e}")
            return {'error': str(e)}


class HostelStudentProcessor:
    """
    Specialized class for hostel student attendance workflow.
    
    Requirements: 2.4, 2.5
    - Implement single-step classroom verification for hostel students
    - Set up hostel student identification and attendance marking
    - Create separate attendance processing logic for hostel students
    """
    
    def __init__(self, attendance_service: AttendanceService):
        self.attendance_service = attendance_service
        self.logger = logging.getLogger(f"{__name__}.HostelStudentProcessor")
    
    async def process_hostel_student_attendance(self, student_id: str, session_id: str, confidence: float) -> bool:
        """
        Process attendance for a hostel student (single-step verification).
        
        Hostel students only need classroom verification, no gate entry required.
        """
        try:
            # Validate student exists and is a hostel student
            student = await self.attendance_service.student_repo.get_student_by_id(student_id)
            if not student:
                self.logger.warning(f"Hostel attendance attempted for non-existent student: {student_id}")
                return False
            
            if student.student_type != StudentType.HOSTEL_STUDENT:
                self.logger.warning(f"Hostel workflow used for non-hostel student: {student_id}")
                return False
            
            if not student.is_active:
                self.logger.warning(f"Hostel attendance attempted for inactive student: {student_id}")
                return False
            
            # Validate session exists and is active
            session = await self.attendance_service.attendance_repo.get_session_by_id(session_id)
            if not session or not session.is_active:
                self.logger.warning(f"Hostel attendance attempted for invalid session: {session_id}")
                return False
            
            # Check if student already marked present in this session
            attendance_records = await self.attendance_service.attendance_repo.get_session_attendance(session_id)
            existing_record = next((r for r in attendance_records 
                                  if r.student_id == student_id and r.status == AttendanceStatus.PRESENT), None)
            
            if existing_record:
                self.logger.debug(f"Hostel student {student_id} already marked present in session {session_id}")
                return True
            
            # Create attendance record for hostel student
            current_time = datetime.utcnow()
            record = AttendanceRecord(
                student_id=student_id,
                session_id=session_id,
                status=AttendanceStatus.PRESENT,
                timestamp=current_time,
                confidence=confidence,
                classroom_entry_time=current_time,
                gate_entry_time=None  # Hostel students don't have gate entry
            )
            
            # Store attendance record
            await self.attendance_service.attendance_repo.create_attendance_record(record)
            
            self.logger.info(f"Hostel student attendance marked: {student_id} in session {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to process hostel student attendance for {student_id}: {e}")
            return False
    
    async def get_hostel_students_in_class(self, class_id: str) -> List[Dict[str, Any]]:
        """Get all hostel students in a specific class."""
        try:
            all_students = await self.attendance_service.student_repo.get_students_by_class(class_id)
            hostel_students = [s for s in all_students if s.student_type == StudentType.HOSTEL_STUDENT and s.is_active]
            
            return [
                {
                    'student_id': student.student_id,
                    'name': student.name,
                    'student_type': student.student_type.value,
                    'enrollment_date': student.enrollment_date.isoformat(),
                    'class_id': student.class_id
                }
                for student in hostel_students
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to get hostel students for class {class_id}: {e}")
            return []
    
    async def validate_hostel_attendance(self, session_id: str) -> Dict[str, Any]:
        """
        Validate hostel student attendance for a session.
        
        Returns validation results including present/absent counts.
        """
        try:
            session = await self.attendance_service.attendance_repo.get_session_by_id(session_id)
            if not session:
                return {'error': 'Session not found'}
            
            # Get all hostel students in the class
            hostel_students = await self.get_hostel_students_in_class(session.class_id)
            
            # Get attendance records for the session
            attendance_records = await self.attendance_service.attendance_repo.get_session_attendance(session_id)
            
            # Filter hostel student attendance records
            hostel_attendance = [r for r in attendance_records 
                               if any(hs['student_id'] == r.student_id for hs in hostel_students)]
            
            present_hostel_ids = {r.student_id for r in hostel_attendance if r.status == AttendanceStatus.PRESENT}
            
            present_students = []
            absent_students = []
            
            for student in hostel_students:
                student_id = student['student_id']
                if student_id in present_hostel_ids:
                    # Find the attendance record
                    record = next(r for r in hostel_attendance if r.student_id == student_id)
                    present_students.append({
                        'student_id': student_id,
                        'name': student['name'],
                        'timestamp': record.timestamp.isoformat(),
                        'confidence': record.confidence
                    })
                else:
                    absent_students.append({
                        'student_id': student_id,
                        'name': student['name']
                    })
            
            total_hostel = len(hostel_students)
            present_count = len(present_students)
            absent_count = len(absent_students)
            attendance_rate = (present_count / total_hostel * 100) if total_hostel > 0 else 0
            
            return {
                'session_id': session_id,
                'total_hostel_students': total_hostel,
                'present_count': present_count,
                'absent_count': absent_count,
                'attendance_rate': round(attendance_rate, 2),
                'present_students': present_students,
                'absent_students': absent_students,
                'validation_status': 'complete'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to validate hostel attendance for session {session_id}: {e}")
            return {'error': str(e)}
    
    async def mark_hostel_student_absent(self, student_id: str, session_id: str, reason: str = "Not detected") -> bool:
        """Mark a hostel student as absent in a session."""
        try:
            # Validate student is hostel student
            student = await self.attendance_service.student_repo.get_student_by_id(student_id)
            if not student or student.student_type != StudentType.HOSTEL_STUDENT:
                return False
            
            # Check if already has attendance record
            attendance_records = await self.attendance_service.attendance_repo.get_session_attendance(session_id)
            existing_record = next((r for r in attendance_records if r.student_id == student_id), None)
            
            if existing_record:
                # Update existing record to absent
                await self.attendance_service.attendance_repo.update_attendance_record(
                    existing_record.id,
                    {
                        'status': AttendanceStatus.ABSENT,
                        'notes': reason
                    }
                )
            else:
                # Create new absent record
                record = AttendanceRecord(
                    student_id=student_id,
                    session_id=session_id,
                    status=AttendanceStatus.ABSENT,
                    timestamp=datetime.utcnow(),
                    confidence=0.0
                )
                await self.attendance_service.attendance_repo.create_attendance_record(record)
            
            self.logger.info(f"Hostel student marked absent: {student_id} - {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to mark hostel student absent {student_id}: {e}")
            return False
    
    async def get_hostel_attendance_summary(self, session_id: str) -> Dict[str, Any]:
        """Get a summary of hostel student attendance for a session."""
        try:
            validation_results = await self.validate_hostel_attendance(session_id)
            
            if 'error' in validation_results:
                return validation_results
            
            return {
                'session_id': session_id,
                'student_type': 'hostel',
                'total_students': validation_results['total_hostel_students'],
                'present_count': validation_results['present_count'],
                'absent_count': validation_results['absent_count'],
                'attendance_rate': validation_results['attendance_rate'],
                'status': 'complete',
                'workflow_type': 'single_step_classroom_only',
                'summary': f"{validation_results['present_count']}/{validation_results['total_hostel_students']} hostel students present ({validation_results['attendance_rate']:.1f}%)"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get hostel attendance summary: {e}")
            return {'error': str(e)}
    
    async def process_bulk_hostel_attendance(self, detections: List[Dict[str, Any]], session_id: str) -> Dict[str, Any]:
        """
        Process multiple hostel student detections at once.
        
        Args:
            detections: List of detection dictionaries with student_id and confidence
            session_id: Session ID for attendance marking
        
        Returns:
            Processing results summary
        """
        try:
            processed_count = 0
            failed_count = 0
            processed_students = []
            failed_students = []
            
            for detection in detections:
                student_id = detection.get('student_id')
                confidence = detection.get('confidence', 0.0)
                
                if not student_id:
                    failed_count += 1
                    continue
                
                success = await self.process_hostel_student_attendance(student_id, session_id, confidence)
                
                if success:
                    processed_count += 1
                    processed_students.append(student_id)
                else:
                    failed_count += 1
                    failed_students.append(student_id)
            
            return {
                'session_id': session_id,
                'total_detections': len(detections),
                'processed_count': processed_count,
                'failed_count': failed_count,
                'processed_students': processed_students,
                'failed_students': failed_students,
                'success_rate': (processed_count / len(detections) * 100) if detections else 0
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process bulk hostel attendance: {e}")
            return {'error': str(e)}
"""
Core interfaces and abstract classes for the Smart Attendance System.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from datetime import datetime
import numpy as np

from backend.models.student import Student, StudentMatch
from backend.models.attendance import AttendanceSession, AttendanceRecord
from backend.models.face_detection import FaceDetection
from backend.models.emotion import EmotionResult, EmotionStatistics


class IFaceRecognitionService(ABC):
    """Interface for face recognition service."""
    
    @abstractmethod
    def detect_faces(self, frame: np.ndarray) -> List[FaceDetection]:
        """Detect faces in a video frame."""
        pass
    
    @abstractmethod
    def extract_embedding(self, face_roi: np.ndarray) -> np.ndarray:
        """Extract face embedding from face region of interest."""
        pass
    
    @abstractmethod
    def match_face(self, embedding: np.ndarray) -> Optional[StudentMatch]:
        """Match face embedding against enrolled students."""
        pass
    
    @abstractmethod
    def verify_liveness(self, face_sequence: List[np.ndarray]) -> bool:
        """Verify if the face is live (anti-spoofing)."""
        pass


class IEmotionAnalysisService(ABC):
    """Interface for emotion analysis service."""
    
    @abstractmethod
    def analyze_emotion(self, face_roi: np.ndarray) -> EmotionResult:
        """Analyze emotion from face region of interest."""
        pass
    
    @abstractmethod
    def calculate_engagement_score(self, emotions: List[EmotionResult]) -> float:
        """Calculate engagement score from emotion results."""
        pass
    
    @abstractmethod
    def get_session_statistics(self, session_id: str) -> EmotionStatistics:
        """Get emotion statistics for a session."""
        pass


class IAttendanceService(ABC):
    """Interface for attendance management service."""
    
    @abstractmethod
    def record_gate_entry(self, student_id: str, timestamp: datetime) -> bool:
        """Record gate entry for a day scholar."""
        pass
    
    @abstractmethod
    def mark_classroom_attendance(self, detections: List[FaceDetection]) -> AttendanceSession:
        """Mark classroom attendance based on face detections."""
        pass
    
    @abstractmethod
    def validate_day_scholar_attendance(self, student_id: str, session_id: str) -> bool:
        """Validate day scholar attendance with cross-verification."""
        pass
    
    @abstractmethod
    def generate_attendance_report(self, session_id: str) -> dict:
        """Generate attendance report for a session."""
        pass


class IValidationService(ABC):
    """Interface for validation service."""
    
    @abstractmethod
    def validate_attendance_count(self, session: AttendanceSession) -> dict:
        """Validate attendance count against registered students."""
        pass
    
    @abstractmethod
    def check_missing_students(self, session: AttendanceSession) -> List[Student]:
        """Check for missing students in attendance."""
        pass
    
    @abstractmethod
    def monitor_system_health(self) -> dict:
        """Monitor system health status."""
        pass


class INotificationService(ABC):
    """Interface for notification service."""
    
    @abstractmethod
    def send_alert(self, message: str, recipients: List[str]) -> bool:
        """Send alert notification."""
        pass
    
    @abstractmethod
    def send_attendance_alert(self, session_id: str, missing_count: int) -> bool:
        """Send attendance discrepancy alert."""
        pass


class ICameraService(ABC):
    """Interface for camera service."""
    
    @abstractmethod
    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """Get current frame from camera."""
        pass
    
    @abstractmethod
    def is_camera_connected(self, camera_id: str) -> bool:
        """Check if camera is connected."""
        pass
    
    @abstractmethod
    def start_stream(self, camera_id: str) -> bool:
        """Start camera stream."""
        pass
    
    @abstractmethod
    def stop_stream(self, camera_id: str) -> bool:
        """Stop camera stream."""
        pass


class IRepository(ABC):
    """Base repository interface."""
    
    @abstractmethod
    def create(self, entity: dict) -> str:
        """Create new entity."""
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: str) -> Optional[dict]:
        """Get entity by ID."""
        pass
    
    @abstractmethod
    def update(self, entity_id: str, data: dict) -> bool:
        """Update entity."""
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """Delete entity."""
        pass
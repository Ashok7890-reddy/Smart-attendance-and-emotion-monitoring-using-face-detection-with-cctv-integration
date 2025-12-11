"""
WebSocket integration service for broadcasting real-time updates.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
import asyncio

from ..models.attendance import AttendanceSession, AttendanceRecord
from ..models.emotion import EmotionResult, EmotionStatistics

logger = logging.getLogger(__name__)


class WebSocketIntegrationService:
    """
    Service for integrating WebSocket broadcasting with attendance and emotion services.
    
    Requirements: 3.5, 5.2, 5.3
    - Implement real-time attendance and emotion statistics broadcasting
    - Set up connection management and error handling
    """
    
    def __init__(self):
        self._connection_manager = None
        self._enabled = True
    
    def set_connection_manager(self, connection_manager):
        """Set the WebSocket connection manager."""
        self._connection_manager = connection_manager
    
    def disable(self):
        """Disable WebSocket broadcasting (for testing)."""
        self._enabled = False
    
    def enable(self):
        """Enable WebSocket broadcasting."""
        self._enabled = True
    
    async def broadcast_attendance_update(self, session: AttendanceSession):
        """
        Broadcast attendance update to WebSocket clients.
        
        Args:
            session: Updated attendance session
        """
        if not self._enabled or not self._connection_manager:
            return
        
        try:
            # Calculate attendance statistics
            attendance_percentage = 0.0
            if session.total_registered > 0:
                attendance_percentage = (session.total_detected / session.total_registered) * 100
            
            # Prepare attendance data
            attendance_data = {
                "session_id": session.session_id,
                "class_id": session.class_id,
                "faculty_id": session.faculty_id,
                "total_registered": session.total_registered,
                "total_detected": session.total_detected,
                "attendance_percentage": round(attendance_percentage, 2),
                "is_active": session.is_active,
                "start_time": session.start_time.isoformat() if session.start_time else None,
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Add present students list
            present_students = []
            for record in session.attendance_records:
                if record.status.value in ["present", "late"]:
                    present_students.append({
                        "student_id": record.student_id,
                        "status": record.status.value,
                        "timestamp": record.timestamp.isoformat() if record.timestamp else None,
                        "confidence": record.confidence
                    })
            
            attendance_data["present_students"] = present_students
            attendance_data["present_count"] = len(present_students)
            
            # Broadcast to session subscribers
            await self._connection_manager.send_attendance_update(
                session.session_id, 
                attendance_data
            )
            
            logger.debug(f"Broadcasted attendance update for session {session.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast attendance update: {str(e)}")
    
    async def broadcast_emotion_update(self, session_id: str, emotion_stats: EmotionStatistics):
        """
        Broadcast emotion statistics update to WebSocket clients.
        
        Args:
            session_id: Session ID
            emotion_stats: Emotion statistics data
        """
        if not self._enabled or not self._connection_manager:
            return
        
        try:
            # Prepare emotion data
            emotion_data = {
                "session_id": session_id,
                "total_detections": emotion_stats.total_detections,
                "emotion_breakdown": emotion_stats.emotion_breakdown,
                "engagement_score": emotion_stats.engagement_score,
                "average_engagement": emotion_stats.average_engagement,
                "timestamp_range": {
                    "start": emotion_stats.start_time.isoformat() if emotion_stats.start_time else None,
                    "end": emotion_stats.end_time.isoformat() if emotion_stats.end_time else None
                },
                "last_updated": datetime.utcnow().isoformat()
            }
            
            # Add recent emotion trends if available
            if hasattr(emotion_stats, 'recent_trends'):
                emotion_data["recent_trends"] = emotion_stats.recent_trends
            
            # Broadcast to session subscribers
            await self._connection_manager.send_emotion_update(session_id, emotion_data)
            
            logger.debug(f"Broadcasted emotion update for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast emotion update: {str(e)}")
    
    async def broadcast_student_detection(self, session_id: str, student_id: str, detection_data: Dict[str, Any]):
        """
        Broadcast individual student detection to WebSocket clients.
        
        Args:
            session_id: Session ID
            student_id: Student ID
            detection_data: Detection data
        """
        if not self._enabled or not self._connection_manager:
            return
        
        try:
            message_data = {
                "session_id": session_id,
                "student_id": student_id,
                "detection_type": detection_data.get("type", "attendance"),
                "timestamp": detection_data.get("timestamp", datetime.utcnow().isoformat()),
                "confidence": detection_data.get("confidence", 0.0),
                "location": detection_data.get("location", "unknown"),
                "metadata": detection_data.get("metadata", {})
            }
            
            # Send as student detection event
            await self._connection_manager.broadcast_to_session(session_id, {
                "type": "student_detection",
                "data": message_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.debug(f"Broadcasted student detection: {student_id} in session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast student detection: {str(e)}")
    
    async def broadcast_validation_alert(self, session_id: str, alert_data: Dict[str, Any]):
        """
        Broadcast validation alert to WebSocket clients.
        
        Args:
            session_id: Session ID
            alert_data: Alert data
        """
        if not self._enabled or not self._connection_manager:
            return
        
        try:
            alert_message = {
                "session_id": session_id,
                "alert_type": alert_data.get("type", "validation"),
                "severity": alert_data.get("severity", "warning"),
                "title": alert_data.get("title", "Validation Alert"),
                "message": alert_data.get("message", ""),
                "details": alert_data.get("details", {}),
                "requires_action": alert_data.get("requires_action", False),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Broadcast alert
            await self._connection_manager.send_alert(alert_message, session_id)
            
            logger.info(f"Broadcasted validation alert for session {session_id}: {alert_message['title']}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast validation alert: {str(e)}")
    
    async def broadcast_system_alert(self, alert_data: Dict[str, Any]):
        """
        Broadcast system-wide alert to all WebSocket clients.
        
        Args:
            alert_data: Alert data
        """
        if not self._enabled or not self._connection_manager:
            return
        
        try:
            alert_message = {
                "alert_type": alert_data.get("type", "system"),
                "severity": alert_data.get("severity", "info"),
                "title": alert_data.get("title", "System Alert"),
                "message": alert_data.get("message", ""),
                "details": alert_data.get("details", {}),
                "requires_action": alert_data.get("requires_action", False),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Broadcast to all connections
            await self._connection_manager.send_alert(alert_message)
            
            logger.info(f"Broadcasted system alert: {alert_message['title']}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast system alert: {str(e)}")
    
    async def broadcast_session_status(self, session_id: str, status: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Broadcast session status change to WebSocket clients.
        
        Args:
            session_id: Session ID
            status: New status (started, ended, paused, resumed)
            metadata: Additional metadata
        """
        if not self._enabled or not self._connection_manager:
            return
        
        try:
            status_data = {
                "session_id": session_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            # Broadcast session status
            await self._connection_manager.broadcast_to_session(session_id, {
                "type": "session_status",
                "data": status_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Broadcasted session status change: {session_id} -> {status}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast session status: {str(e)}")
    
    async def broadcast_camera_status(self, camera_id: str, status: str, location: str):
        """
        Broadcast camera status change to WebSocket clients.
        
        Args:
            camera_id: Camera identifier
            status: Camera status (online, offline, error)
            location: Camera location (gate, classroom)
        """
        if not self._enabled or not self._connection_manager:
            return
        
        try:
            status_data = {
                "camera_id": camera_id,
                "status": status,
                "location": location,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Broadcast camera status to all connections
            await self._connection_manager.broadcast_to_all({
                "type": "camera_status",
                "data": status_data,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Broadcasted camera status: {camera_id} ({location}) -> {status}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast camera status: {str(e)}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        if not self._connection_manager:
            return {"error": "Connection manager not available"}
        
        try:
            return {
                "total_connections": self._connection_manager.get_connection_count(),
                "session_subscriptions": {
                    session_id: self._connection_manager.get_session_subscriber_count(session_id)
                    for session_id in self._connection_manager.session_subscriptions.keys()
                },
                "enabled": self._enabled,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get connection stats: {str(e)}")
            return {"error": str(e)}


# Global instance
websocket_integration = WebSocketIntegrationService()


def get_websocket_integration() -> WebSocketIntegrationService:
    """Get the WebSocket integration service instance."""
    return websocket_integration
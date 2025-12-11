"""
Notification service for the Smart Attendance System.
Handles alerts and notifications for attendance discrepancies and system issues.
Implements real-time alerting, escalation workflows, and acknowledgment tracking.
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid

from backend.core.base_service import BaseService
from backend.core.interfaces import INotificationService


class NotificationType(Enum):
    """Notification type enumeration."""
    ATTENDANCE_ALERT = "attendance_alert"
    SYSTEM_HEALTH = "system_health"
    VALIDATION_ERROR = "validation_error"
    MISSING_STUDENTS = "missing_students"
    CAMERA_CONNECTIVITY = "camera_connectivity"
    FACE_RECOGNITION_CONFIDENCE = "face_recognition_confidence"
    PERFORMANCE_ALERT = "performance_alert"
    ESCALATION_ALERT = "escalation_alert"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(Enum):
    """Notification status enumeration."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"
    FAILED = "failed"


class NotificationChannel(Enum):
    """Notification delivery channels."""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    DASHBOARD = "dashboard"


@dataclass
class NotificationRecipient:
    """Notification recipient model."""
    recipient_id: str
    name: str
    role: str  # faculty, admin, tech_support
    channels: List[NotificationChannel]
    contact_info: Dict[str, str]  # email, phone, etc.
    escalation_delay_minutes: int = 15


@dataclass
class NotificationMessage:
    """Enhanced notification message model."""
    message_id: str
    type: NotificationType
    title: str
    message: str
    recipients: List[str]
    priority: NotificationPriority
    timestamp: datetime
    status: NotificationStatus = NotificationStatus.PENDING
    channels: List[NotificationChannel] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    acknowledgments: Dict[str, datetime] = field(default_factory=dict)
    escalation_attempts: int = 0
    max_escalation_attempts: int = 3
    escalation_delay_minutes: int = 15
    expires_at: Optional[datetime] = None
    requires_acknowledgment: bool = False


class NotificationService(BaseService, INotificationService):
    """
    Enhanced notification service with real-time alerting, escalation workflows,
    and acknowledgment tracking.
    
    Requirements: 7.1, 7.2, 7.3
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self.notification_queue: List[NotificationMessage] = []
        self.sent_notifications: List[NotificationMessage] = []
        self.recipients: Dict[str, NotificationRecipient] = {}
        self.websocket_connections: Set = set()
        self.escalation_tasks: Dict[str, asyncio.Task] = {}
        self.notification_handlers: Dict[NotificationChannel, Callable] = {}
        
        # Initialize default recipients
        self._initialize_default_recipients()
        
        # Initialize notification handlers
        self._initialize_notification_handlers()
        
        # Performance monitoring thresholds
        self.face_recognition_confidence_threshold = 0.85
        self.processing_time_threshold_seconds = 5.0
        
        # Start background tasks (in a real implementation, these would be managed properly)
        # For now, we'll handle them synchronously to avoid async complexity in this demo
    
    def _initialize_default_recipients(self):
        """Initialize default notification recipients."""
        self.recipients = {
            "faculty": NotificationRecipient(
                recipient_id="faculty",
                name="Faculty",
                role="faculty",
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.DASHBOARD, NotificationChannel.EMAIL],
                contact_info={"email": "faculty@institution.edu"},
                escalation_delay_minutes=10
            ),
            "admin": NotificationRecipient(
                recipient_id="admin",
                name="Administrator",
                role="admin",
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL, NotificationChannel.SMS],
                contact_info={"email": "admin@institution.edu", "phone": "+1234567890"},
                escalation_delay_minutes=5
            ),
            "tech_support": NotificationRecipient(
                recipient_id="tech_support",
                name="Technical Support",
                role="tech_support",
                channels=[NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.PUSH],
                contact_info={"email": "tech@institution.edu", "phone": "+1234567891"},
                escalation_delay_minutes=15
            )
        }
    
    def _initialize_notification_handlers(self):
        """Initialize notification channel handlers."""
        self.notification_handlers = {
            NotificationChannel.WEBSOCKET: self._send_websocket_notification,
            NotificationChannel.EMAIL: self._send_email_notification,
            NotificationChannel.SMS: self._send_sms_notification,
            NotificationChannel.PUSH: self._send_push_notification,
            NotificationChannel.DASHBOARD: self._send_dashboard_notification
        }
    
    def send_alert(self, message: str, recipients: List[str], 
                   priority: NotificationPriority = NotificationPriority.HIGH,
                   requires_acknowledgment: bool = False) -> bool:
        """
        Send enhanced alert notification with escalation support.
        
        Args:
            message: Alert message
            recipients: List of recipient identifiers
            priority: Notification priority level
            requires_acknowledgment: Whether acknowledgment is required
            
        Returns:
            bool: True if alert was queued successfully
        """
        try:
            notification = NotificationMessage(
                message_id=str(uuid.uuid4()),
                type=NotificationType.SYSTEM_HEALTH,
                title="System Alert",
                message=message,
                recipients=recipients,
                priority=priority,
                timestamp=datetime.now(),
                requires_acknowledgment=requires_acknowledgment,
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
            self.logger.warning(f"ALERT: {message} - Recipients: {recipients}")
            self._queue_notification(notification)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send alert: {str(e)}")
            return False
    
    def send_attendance_alert(self, session_id: str, missing_count: int, 
                            missing_students: List[str] = None) -> bool:
        """
        Send enhanced attendance discrepancy alert with real-time delivery.
        
        Requirements: 7.1 - Real-time alerts for attendance discrepancies
        
        Args:
            session_id: Attendance session ID
            missing_count: Number of missing students
            missing_students: List of missing student IDs
            
        Returns:
            bool: True if alert was sent successfully
        """
        try:
            if missing_count == 0:
                return True  # No alert needed
            
            # Determine priority based on missing count
            if missing_count > 10:
                priority = NotificationPriority.CRITICAL
                requires_ack = True
            elif missing_count > 5:
                priority = NotificationPriority.HIGH
                requires_ack = True
            else:
                priority = NotificationPriority.MEDIUM
                requires_ack = False
            
            message = f"Attendance Alert: {missing_count} students missing in session {session_id}"
            if missing_students:
                message += f". Missing students: {', '.join(missing_students[:5])}"
                if len(missing_students) > 5:
                    message += f" and {len(missing_students) - 5} more"
            
            notification = NotificationMessage(
                message_id=str(uuid.uuid4()),
                type=NotificationType.ATTENDANCE_ALERT,
                title="Attendance Discrepancy",
                message=message,
                recipients=["faculty", "admin"],
                priority=priority,
                timestamp=datetime.now(),
                requires_acknowledgment=requires_ack,
                metadata={
                    "session_id": session_id,
                    "missing_count": missing_count,
                    "missing_students": missing_students or []
                }
            )
            
            self.logger.warning(f"ATTENDANCE ALERT: {message}")
            self._queue_notification(notification)
            
            # Send immediate real-time notification for critical cases
            if priority == NotificationPriority.CRITICAL:
                self._send_real_time_alert(notification)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send attendance alert: {str(e)}")
            return False
    
    def send_camera_connectivity_alert(self, camera_id: str, is_connected: bool) -> bool:
        """
        Send camera connectivity alert.
        
        Requirements: 7.2 - Camera connectivity notifications
        
        Args:
            camera_id: Camera identifier
            is_connected: Whether camera is connected
            
        Returns:
            bool: True if alert was sent successfully
        """
        try:
            if is_connected:
                message = f"Camera {camera_id} connectivity restored"
                priority = NotificationPriority.MEDIUM
                title = "Camera Connectivity Restored"
            else:
                message = f"Camera {camera_id} connectivity lost - immediate attention required"
                priority = NotificationPriority.CRITICAL
                title = "Camera Connectivity Lost"
            
            notification = NotificationMessage(
                message_id=str(uuid.uuid4()),
                type=NotificationType.CAMERA_CONNECTIVITY,
                title=title,
                message=message,
                recipients=["admin", "tech_support"],
                priority=priority,
                timestamp=datetime.now(),
                requires_acknowledgment=not is_connected,  # Require ack for disconnections
                metadata={
                    "camera_id": camera_id,
                    "is_connected": is_connected
                }
            )
            
            self.logger.warning(f"CAMERA ALERT: {message}")
            self._queue_notification(notification)
            
            # Send immediate notification for disconnections
            if not is_connected:
                self._send_real_time_alert(notification)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send camera connectivity alert: {str(e)}")
            return False
    
    def send_face_recognition_confidence_alert(self, session_id: str, 
                                             low_confidence_count: int,
                                             average_confidence: float) -> bool:
        """
        Send face recognition confidence alert.
        
        Requirements: 7.3 - Face recognition confidence monitoring
        
        Args:
            session_id: Session ID
            low_confidence_count: Number of low confidence detections
            average_confidence: Average confidence score
            
        Returns:
            bool: True if alert was sent successfully
        """
        try:
            if average_confidence >= self.face_recognition_confidence_threshold:
                return True  # No alert needed
            
            priority = NotificationPriority.HIGH if average_confidence < 0.7 else NotificationPriority.MEDIUM
            
            message = (f"Face recognition confidence alert for session {session_id}: "
                      f"{low_confidence_count} detections below 85% confidence. "
                      f"Average confidence: {average_confidence:.2%}")
            
            notification = NotificationMessage(
                message_id=str(uuid.uuid4()),
                type=NotificationType.FACE_RECOGNITION_CONFIDENCE,
                title="Face Recognition Confidence Alert",
                message=message,
                recipients=["admin", "tech_support"],
                priority=priority,
                timestamp=datetime.now(),
                requires_acknowledgment=True,
                metadata={
                    "session_id": session_id,
                    "low_confidence_count": low_confidence_count,
                    "average_confidence": average_confidence,
                    "threshold": self.face_recognition_confidence_threshold
                }
            )
            
            self.logger.warning(f"CONFIDENCE ALERT: {message}")
            self._queue_notification(notification)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send face recognition confidence alert: {str(e)}")
            return False
    
    def send_performance_alert(self, component: str, processing_time: float,
                             threshold: float = None) -> bool:
        """
        Send performance alert for slow processing.
        
        Requirements: 7.4 - Performance monitoring alerts
        
        Args:
            component: Component name (e.g., 'face_recognition', 'emotion_analysis')
            processing_time: Actual processing time in seconds
            threshold: Performance threshold (defaults to class threshold)
            
        Returns:
            bool: True if alert was sent successfully
        """
        try:
            threshold = threshold or self.processing_time_threshold_seconds
            
            if processing_time <= threshold:
                return True  # No alert needed
            
            priority = NotificationPriority.CRITICAL if processing_time > (threshold * 2) else NotificationPriority.HIGH
            
            message = (f"Performance alert: {component} processing time exceeded threshold. "
                      f"Processing time: {processing_time:.2f}s (threshold: {threshold}s)")
            
            notification = NotificationMessage(
                message_id=str(uuid.uuid4()),
                type=NotificationType.PERFORMANCE_ALERT,
                title="Performance Alert",
                message=message,
                recipients=["admin", "tech_support"],
                priority=priority,
                timestamp=datetime.now(),
                requires_acknowledgment=True,
                metadata={
                    "component": component,
                    "processing_time": processing_time,
                    "threshold": threshold,
                    "performance_ratio": processing_time / threshold
                }
            )
            
            self.logger.warning(f"PERFORMANCE ALERT: {message}")
            self._queue_notification(notification)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send performance alert: {str(e)}")
            return False
    
    def send_validation_error_alert(self, session_id: str, error_message: str) -> bool:
        """
        Send validation error alert.
        
        Args:
            session_id: Session ID where validation failed
            error_message: Error description
            
        Returns:
            bool: True if alert was sent successfully
        """
        try:
            notification = NotificationMessage(
                message_id=str(uuid.uuid4()),
                type=NotificationType.VALIDATION_ERROR,
                title="Validation Error",
                message=f"Validation failed for session {session_id}: {error_message}",
                recipients=["admin", "tech_support"],
                priority=NotificationPriority.HIGH,
                timestamp=datetime.now(),
                requires_acknowledgment=True,
                metadata={
                    "session_id": session_id,
                    "error": error_message
                }
            )
            
            self.logger.error(f"VALIDATION ERROR: {notification.message}")
            self._queue_notification(notification)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send validation error alert: {str(e)}")
            return False
    
    def acknowledge_notification(self, message_id: str, recipient_id: str) -> bool:
        """
        Acknowledge a notification.
        
        Requirements: 7.3 - Acknowledgment workflows
        
        Args:
            message_id: Notification message ID
            recipient_id: ID of recipient acknowledging
            
        Returns:
            bool: True if acknowledgment was recorded
        """
        try:
            # Find notification in sent notifications
            for notification in self.sent_notifications:
                if notification.message_id == message_id:
                    notification.acknowledgments[recipient_id] = datetime.now()
                    
                    # Check if all required recipients have acknowledged
                    if len(notification.acknowledgments) >= len(notification.recipients):
                        notification.status = NotificationStatus.ACKNOWLEDGED
                        self.logger.info(f"Notification {message_id} fully acknowledged")
                    
                    return True
            
            # Also check pending notifications
            for notification in self.notification_queue:
                if notification.message_id == message_id:
                    notification.acknowledgments[recipient_id] = datetime.now()
                    return True
            
            self.logger.warning(f"Notification {message_id} not found for acknowledgment")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to acknowledge notification: {str(e)}")
            return False
    
    def get_pending_notifications(self, recipient_id: str = None) -> List[NotificationMessage]:
        """
        Get pending notifications, optionally filtered by recipient.
        
        Args:
            recipient_id: Optional recipient filter
            
        Returns:
            List of pending notifications
        """
        try:
            notifications = self.notification_queue.copy()
            
            if recipient_id:
                notifications = [n for n in notifications if recipient_id in n.recipients]
            
            # Sort by priority and timestamp
            priority_order = {
                NotificationPriority.CRITICAL: 0,
                NotificationPriority.HIGH: 1,
                NotificationPriority.MEDIUM: 2,
                NotificationPriority.LOW: 3
            }
            
            notifications.sort(key=lambda n: (priority_order[n.priority], n.timestamp))
            
            return notifications
            
        except Exception as e:
            self.logger.error(f"Failed to get pending notifications: {str(e)}")
            return []
    
    def get_unacknowledged_notifications(self, recipient_id: str = None) -> List[NotificationMessage]:
        """
        Get unacknowledged notifications requiring attention.
        
        Args:
            recipient_id: Optional recipient filter
            
        Returns:
            List of unacknowledged notifications
        """
        try:
            unacknowledged = []
            
            for notification in self.sent_notifications:
                if (notification.requires_acknowledgment and 
                    notification.status != NotificationStatus.ACKNOWLEDGED):
                    
                    if recipient_id:
                        if (recipient_id in notification.recipients and 
                            recipient_id not in notification.acknowledgments):
                            unacknowledged.append(notification)
                    else:
                        unacknowledged.append(notification)
            
            return unacknowledged
            
        except Exception as e:
            self.logger.error(f"Failed to get unacknowledged notifications: {str(e)}")
            return []
    
    def _queue_notification(self, notification: NotificationMessage):
        """Queue notification for processing."""
        self.notification_queue.append(notification)
        
        # Process immediately for critical notifications
        if notification.priority == NotificationPriority.CRITICAL:
            self._process_notification(notification)
    
    def _process_notification(self, notification: NotificationMessage):
        """Process a single notification through all channels."""
        try:
            # Determine channels based on recipients
            channels = set()
            for recipient_id in notification.recipients:
                if recipient_id in self.recipients:
                    recipient = self.recipients[recipient_id]
                    channels.update(recipient.channels)
            
            notification.channels = list(channels)
            
            # Send through each channel
            success_count = 0
            for channel in channels:
                if channel in self.notification_handlers:
                    try:
                        success = self.notification_handlers[channel](notification)
                        if success:
                            success_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to send via {channel}: {str(e)}")
            
            # Update status
            if success_count > 0:
                notification.status = NotificationStatus.SENT
                self.sent_notifications.append(notification)
                
                # Schedule escalation if required
                if notification.requires_acknowledgment:
                    self._schedule_escalation(notification)
            else:
                notification.status = NotificationStatus.FAILED
                self.logger.error(f"Failed to send notification {notification.message_id}")
            
        except Exception as e:
            self.logger.error(f"Error processing notification: {str(e)}")
            notification.status = NotificationStatus.FAILED
    
    def _send_real_time_alert(self, notification: NotificationMessage):
        """Send immediate real-time alert for critical notifications."""
        try:
            # Send via WebSocket for immediate delivery
            self._send_websocket_notification(notification)
            
            # Log critical alert
            self.logger.critical(f"REAL-TIME ALERT: {notification.message}")
            
        except Exception as e:
            self.logger.error(f"Failed to send real-time alert: {str(e)}")
    
    def _schedule_escalation(self, notification: NotificationMessage):
        """Schedule escalation for unacknowledged notifications."""
        # In a real implementation, this would use a proper task scheduler
        # For now, we'll just log the escalation schedule
        escalation_time = notification.timestamp + timedelta(minutes=notification.escalation_delay_minutes)
        self.logger.info(f"Escalation scheduled for notification {notification.message_id} at {escalation_time}")
    
    def _escalate_notification(self, notification: NotificationMessage):
        """Escalate unacknowledged notification."""
        try:
            notification.escalation_attempts += 1
            notification.status = NotificationStatus.ESCALATED
            
            escalation_message = (f"ESCALATION #{notification.escalation_attempts}: "
                                f"Unacknowledged alert - {notification.message}")
            
            escalation_notification = NotificationMessage(
                message_id=str(uuid.uuid4()),
                type=NotificationType.ESCALATION_ALERT,
                title=f"Escalated Alert #{notification.escalation_attempts}",
                message=escalation_message,
                recipients=["admin", "tech_support"],  # Escalate to higher level
                priority=NotificationPriority.CRITICAL,
                timestamp=datetime.now(),
                requires_acknowledgment=True,
                metadata={
                    "original_message_id": notification.message_id,
                    "escalation_attempt": notification.escalation_attempts,
                    "original_timestamp": notification.timestamp
                }
            )
            
            self.logger.critical(f"ESCALATION: {escalation_message}")
            self._queue_notification(escalation_notification)
            
        except Exception as e:
            self.logger.error(f"Failed to escalate notification: {str(e)}")
    
    # Notification channel handlers (simplified implementations)
    def _send_websocket_notification(self, notification: NotificationMessage) -> bool:
        """Send notification via WebSocket."""
        try:
            # In a real implementation, this would send to connected WebSocket clients
            self.logger.info(f"WebSocket notification sent: {notification.title}")
            return True
        except Exception as e:
            self.logger.error(f"WebSocket notification failed: {str(e)}")
            return False
    
    def _send_email_notification(self, notification: NotificationMessage) -> bool:
        """Send notification via email."""
        try:
            # In a real implementation, this would use an email service
            self.logger.info(f"Email notification sent: {notification.title}")
            return True
        except Exception as e:
            self.logger.error(f"Email notification failed: {str(e)}")
            return False
    
    def _send_sms_notification(self, notification: NotificationMessage) -> bool:
        """Send notification via SMS."""
        try:
            # In a real implementation, this would use an SMS service
            self.logger.info(f"SMS notification sent: {notification.title}")
            return True
        except Exception as e:
            self.logger.error(f"SMS notification failed: {str(e)}")
            return False
    
    def _send_push_notification(self, notification: NotificationMessage) -> bool:
        """Send push notification."""
        try:
            # In a real implementation, this would use a push notification service
            self.logger.info(f"Push notification sent: {notification.title}")
            return True
        except Exception as e:
            self.logger.error(f"Push notification failed: {str(e)}")
            return False
    
    def _send_dashboard_notification(self, notification: NotificationMessage) -> bool:
        """Send notification to dashboard."""
        try:
            # In a real implementation, this would update the dashboard
            self.logger.info(f"Dashboard notification sent: {notification.title}")
            return True
        except Exception as e:
            self.logger.error(f"Dashboard notification failed: {str(e)}")
            return False
    
    def mark_notification_sent(self, message_id: str) -> bool:
        """Mark a notification as sent (legacy method for compatibility)."""
        try:
            for i, notification in enumerate(self.notification_queue):
                if notification.message_id == message_id:
                    notification.status = NotificationStatus.SENT
                    sent_notification = self.notification_queue.pop(i)
                    self.sent_notifications.append(sent_notification)
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to mark notification as sent: {str(e)}")
            return False
    
    def get_notification_history(self, limit: int = 50) -> List[NotificationMessage]:
        """Get notification history."""
        return self.sent_notifications[-limit:]
    
    def clear_old_notifications(self, days: int = 7) -> int:
        """Clear notifications older than specified days."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Clear from sent notifications
            original_count = len(self.sent_notifications)
            self.sent_notifications = [
                n for n in self.sent_notifications 
                if n.timestamp > cutoff_date
            ]
            
            # Clear from pending notifications (older than 1 day)
            day_cutoff = datetime.now() - timedelta(days=1)
            self.notification_queue = [
                n for n in self.notification_queue 
                if n.timestamp > day_cutoff
            ]
            
            cleared_count = original_count - len(self.sent_notifications)
            self.logger.info(f"Cleared {cleared_count} old notifications")
            
            return cleared_count
            
        except Exception as e:
            self.logger.error(f"Failed to clear old notifications: {str(e)}")
            return 0
    
    def get_notification_statistics(self) -> Dict:
        """Get notification system statistics."""
        try:
            total_sent = len(self.sent_notifications)
            pending_count = len(self.notification_queue)
            
            # Count by priority
            priority_counts = {}
            for priority in NotificationPriority:
                priority_counts[priority.value] = len([
                    n for n in self.sent_notifications 
                    if n.priority == priority
                ])
            
            # Count by type
            type_counts = {}
            for notification_type in NotificationType:
                type_counts[notification_type.value] = len([
                    n for n in self.sent_notifications 
                    if n.type == notification_type
                ])
            
            # Acknowledgment statistics
            requiring_ack = [n for n in self.sent_notifications if n.requires_acknowledgment]
            acknowledged = [n for n in requiring_ack if n.status == NotificationStatus.ACKNOWLEDGED]
            
            return {
                "total_sent": total_sent,
                "pending_count": pending_count,
                "priority_distribution": priority_counts,
                "type_distribution": type_counts,
                "acknowledgment_stats": {
                    "requiring_acknowledgment": len(requiring_ack),
                    "acknowledged": len(acknowledged),
                    "acknowledgment_rate": len(acknowledged) / len(requiring_ack) if requiring_ack else 0
                },
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get notification statistics: {str(e)}")
            return {"error": str(e), "timestamp": datetime.now()}
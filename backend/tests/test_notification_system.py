"""
Tests for the enhanced notification and alerting system.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from backend.services.notification_service import (
    NotificationService, NotificationMessage, NotificationPriority, 
    NotificationStatus, NotificationType
)
from backend.services.alert_escalation_manager import AlertEscalationManager
from backend.services.websocket_notification_server import WebSocketNotificationServer
from backend.services.notification_integration_service import NotificationIntegrationService


class TestNotificationService:
    """Test the enhanced notification service."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.notification_service = NotificationService(None)
    
    def test_send_attendance_alert(self):
        """Test sending attendance alert."""
        # Test with missing students
        result = self.notification_service.send_attendance_alert(
            session_id="test_session_001",
            missing_count=5,
            missing_students=["STU001", "STU002", "STU003"]
        )
        
        assert result is True
        
        # Check notification was queued
        pending = self.notification_service.get_pending_notifications()
        assert len(pending) == 1
        
        notification = pending[0]
        assert notification.type == NotificationType.ATTENDANCE_ALERT
        assert notification.priority == NotificationPriority.MEDIUM
        assert "5 students missing" in notification.message
        assert "test_session_001" in notification.message
    
    def test_send_camera_connectivity_alert(self):
        """Test sending camera connectivity alert."""
        # Test camera disconnection
        result = self.notification_service.send_camera_connectivity_alert(
            camera_id="CAM001",
            is_connected=False
        )
        
        assert result is True
        
        # Check notification was queued
        pending = self.notification_service.get_pending_notifications()
        assert len(pending) == 1
        
        notification = pending[0]
        assert notification.type == NotificationType.CAMERA_CONNECTIVITY
        assert notification.priority == NotificationPriority.CRITICAL
        assert notification.requires_acknowledgment is True
        assert "CAM001" in notification.message
        assert "connectivity lost" in notification.message
    
    def test_send_face_recognition_confidence_alert(self):
        """Test sending face recognition confidence alert."""
        result = self.notification_service.send_face_recognition_confidence_alert(
            session_id="test_session_002",
            low_confidence_count=10,
            average_confidence=0.75
        )
        
        assert result is True
        
        # Check notification was queued
        pending = self.notification_service.get_pending_notifications()
        assert len(pending) == 1
        
        notification = pending[0]
        assert notification.type == NotificationType.FACE_RECOGNITION_CONFIDENCE
        assert notification.priority == NotificationPriority.MEDIUM  # 0.75 confidence gives MEDIUM priority
        assert "test_session_002" in notification.message
        assert "75.00%" in notification.message
    
    def test_send_performance_alert(self):
        """Test sending performance alert."""
        result = self.notification_service.send_performance_alert(
            component="face_recognition",
            processing_time=8.5
        )
        
        assert result is True
        
        # Check notification was queued
        pending = self.notification_service.get_pending_notifications()
        assert len(pending) == 1
        
        notification = pending[0]
        assert notification.type == NotificationType.PERFORMANCE_ALERT
        assert notification.priority == NotificationPriority.HIGH  # 8.5s gives HIGH priority (not 2x threshold)
        assert "face_recognition" in notification.message
        assert "8.50s" in notification.message
    
    def test_acknowledge_notification(self):
        """Test notification acknowledgment."""
        # Send a notification that requires acknowledgment
        self.notification_service.send_attendance_alert(
            session_id="test_session_003",
            missing_count=15  # This should require acknowledgment
        )
        
        pending = self.notification_service.get_pending_notifications()
        notification = pending[0]
        message_id = notification.message_id
        
        # Acknowledge the notification
        result = self.notification_service.acknowledge_notification(
            message_id, "faculty"
        )
        
        assert result is True
        
        # Check acknowledgment was recorded
        assert "faculty" in notification.acknowledgments
    
    def test_notification_priority_filtering(self):
        """Test notification priority filtering."""
        # Send notifications with different priorities
        self.notification_service.send_alert(
            "Low priority alert", ["faculty"], NotificationPriority.LOW
        )
        self.notification_service.send_alert(
            "Critical alert", ["admin"], NotificationPriority.CRITICAL
        )
        
        pending = self.notification_service.get_pending_notifications()
        assert len(pending) == 2
        
        # Check that critical notifications come first
        assert pending[0].priority == NotificationPriority.CRITICAL
        assert pending[1].priority == NotificationPriority.LOW
    
    def test_notification_statistics(self):
        """Test notification statistics."""
        # Send various notifications
        self.notification_service.send_attendance_alert("session1", 3)
        self.notification_service.send_camera_connectivity_alert("CAM001", False)
        self.notification_service.send_performance_alert("emotion_analysis", 6.0)
        
        stats = self.notification_service.get_notification_statistics()
        
        assert "total_sent" in stats
        assert "pending_count" in stats
        assert stats["pending_count"] == 3
        assert "priority_distribution" in stats
        assert "type_distribution" in stats


class TestAlertEscalationManager:
    """Test the alert escalation manager."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.notification_service = Mock()
        self.escalation_manager = AlertEscalationManager(self.notification_service)
    
    def test_register_notification_for_escalation(self):
        """Test registering notification for escalation."""
        notification = NotificationMessage(
            message_id="test_msg_001",
            type=NotificationType.ATTENDANCE_ALERT,
            title="Test Alert",
            message="Test message",
            recipients=["faculty"],
            priority=NotificationPriority.HIGH,
            timestamp=datetime.now(),
            requires_acknowledgment=True
        )
        
        result = self.escalation_manager.register_notification_for_escalation(notification)
        assert result is True
        
        # Check escalation was registered
        active_escalations = self.escalation_manager.get_active_escalations()
        assert len(active_escalations) == 1
        assert active_escalations[0]["message_id"] == "test_msg_001"
    
    def test_acknowledge_notification_stops_escalation(self):
        """Test that acknowledging notification stops escalation."""
        notification = NotificationMessage(
            message_id="test_msg_002",
            type=NotificationType.CAMERA_CONNECTIVITY,
            title="Camera Alert",
            message="Camera disconnected",
            recipients=["admin"],
            priority=NotificationPriority.CRITICAL,
            timestamp=datetime.now(),
            requires_acknowledgment=True
        )
        
        # Register for escalation
        self.escalation_manager.register_notification_for_escalation(notification)
        
        # Acknowledge the notification
        result = self.escalation_manager.acknowledge_notification("test_msg_002", "admin")
        assert result is True
        
        # Check escalation was resolved
        active_escalations = self.escalation_manager.get_active_escalations()
        escalation = next((e for e in active_escalations if e["message_id"] == "test_msg_002"), None)
        assert escalation is None or escalation["acknowledged"] is True
    
    def test_escalation_statistics(self):
        """Test escalation statistics."""
        # Register multiple escalations
        for i in range(3):
            notification = NotificationMessage(
                message_id=f"test_msg_{i}",
                type=NotificationType.ATTENDANCE_ALERT,
                title=f"Test Alert {i}",
                message=f"Test message {i}",
                recipients=["faculty"],
                priority=NotificationPriority.HIGH,
                timestamp=datetime.now(),
                requires_acknowledgment=True
            )
            self.escalation_manager.register_notification_for_escalation(notification)
        
        stats = self.escalation_manager.get_escalation_statistics()
        
        assert "total_escalations" in stats
        assert "active_escalations" in stats
        assert stats["total_escalations"] == 3
        assert stats["active_escalations"] == 3
        assert "type_distribution" in stats


class TestWebSocketNotificationServer:
    """Test the WebSocket notification server."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.websocket_server = WebSocketNotificationServer(port=8766)  # Use different port for testing
    
    def test_server_initialization(self):
        """Test server initialization."""
        assert self.websocket_server.host == "localhost"
        assert self.websocket_server.port == 8766
        assert len(self.websocket_server.connected_clients) == 0
    
    def test_server_statistics(self):
        """Test server statistics."""
        stats = self.websocket_server.get_server_statistics()
        
        assert "connected_clients" in stats
        assert "authenticated_clients" in stats
        assert "server_host" in stats
        assert "server_port" in stats
        assert stats["connected_clients"] == 0
        assert stats["server_host"] == "localhost"
        assert stats["server_port"] == 8766
    
    @pytest.mark.asyncio
    async def test_broadcast_notification(self):
        """Test broadcasting notification (without actual WebSocket connections)."""
        notification = NotificationMessage(
            message_id="test_broadcast_001",
            type=NotificationType.SYSTEM_HEALTH,
            title="Test Broadcast",
            message="Test broadcast message",
            recipients=["faculty"],
            priority=NotificationPriority.MEDIUM,
            timestamp=datetime.now()
        )
        
        # This should not raise an exception even with no connected clients
        await self.websocket_server.broadcast_notification(notification)
        
        # Verify no errors occurred
        assert True


class TestNotificationIntegrationService:
    """Test the notification integration service."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.integration_service = NotificationIntegrationService(None)
    
    def test_service_initialization(self):
        """Test service initialization."""
        assert self.integration_service.notification_service is not None
        assert self.integration_service.websocket_server is not None
        assert self.integration_service.escalation_manager is not None
        assert self.integration_service.is_running is False
    
    def test_send_attendance_alert_integration(self):
        """Test sending attendance alert through integration service."""
        result = self.integration_service.send_attendance_alert(
            session_id="integration_test_001",
            missing_count=7,
            missing_students=["STU001", "STU002"]
        )
        
        assert result is True
        
        # Check notification was created
        pending = self.integration_service.notification_service.get_pending_notifications()
        assert len(pending) == 1
        assert "7 students missing" in pending[0].message
    
    def test_acknowledge_notification_integration(self):
        """Test acknowledging notification through integration service."""
        # Send notification that requires acknowledgment
        self.integration_service.send_camera_connectivity_alert("CAM002", False)
        
        pending = self.integration_service.notification_service.get_pending_notifications()
        message_id = pending[0].message_id
        
        # Acknowledge through integration service
        result = self.integration_service.acknowledge_notification(message_id, "admin")
        assert result is True
    
    def test_get_system_status(self):
        """Test getting comprehensive system status."""
        status = self.integration_service.get_system_status()
        
        assert "notification_service" in status
        assert "escalation_manager" in status
        assert "websocket_server" in status
        assert "integration_status" in status
        
        # Check integration status
        integration_status = status["integration_status"]
        assert "is_running" in integration_status
        assert "background_tasks" in integration_status
        assert "timestamp" in integration_status
    
    def test_get_active_alerts(self):
        """Test getting active alerts."""
        # Send some alerts
        self.integration_service.send_attendance_alert("session_001", 5)
        self.integration_service.send_camera_connectivity_alert("CAM003", False)
        
        alerts = self.integration_service.get_active_alerts()
        
        assert "pending_notifications" in alerts
        assert "unacknowledged_notifications" in alerts
        assert "active_escalations" in alerts
        assert "summary" in alerts
        
        # Check summary
        summary = alerts["summary"]
        assert summary["total_pending"] == 2
        assert "timestamp" in summary


# Integration test
def test_complete_notification_workflow():
    """Test complete notification workflow from alert to acknowledgment."""
    # Initialize services
    integration_service = NotificationIntegrationService(None)
    
    # Send critical alert
    result = integration_service.send_camera_connectivity_alert("CAM_CRITICAL", False)
    assert result is True
    
    # Check alert was created
    alerts = integration_service.get_active_alerts()
    assert alerts["summary"]["total_pending"] == 1
    
    # Get the notification
    pending = integration_service.notification_service.get_pending_notifications()
    notification = pending[0]
    
    # Verify it's critical and requires acknowledgment
    assert notification.priority == NotificationPriority.CRITICAL
    assert notification.requires_acknowledgment is True
    
    # Acknowledge the notification
    ack_result = integration_service.acknowledge_notification(
        notification.message_id, "admin"
    )
    assert ack_result is True
    
    # Verify acknowledgment was recorded
    assert "admin" in notification.acknowledgments
    
    print("✅ Complete notification workflow test passed")


if __name__ == "__main__":
    # Run the integration test
    test_complete_notification_workflow()
    print("All notification system tests completed successfully!")
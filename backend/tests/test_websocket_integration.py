"""
Tests for WebSocket integration functionality.
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from backend.api.websocket import ConnectionManager, connection_manager
from backend.services.websocket_integration_service import WebSocketIntegrationService
from backend.models.attendance import AttendanceSession, AttendanceRecord, AttendanceStatus
from backend.models.emotion import EmotionStatistics, EmotionType


class TestConnectionManager:
    """Test cases for WebSocket ConnectionManager."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh ConnectionManager instance for testing."""
        return ConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = Mock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_connect_websocket(self, manager, mock_websocket):
        """Test WebSocket connection establishment."""
        connection_id = "test-connection-1"
        user_info = {"user_id": "test-user", "role": "faculty"}
        
        await manager.connect(mock_websocket, connection_id, user_info)
        
        # Verify connection was established
        assert connection_id in manager.active_connections
        assert manager.active_connections[connection_id] == mock_websocket
        assert connection_id in manager.connection_metadata
        assert manager.connection_metadata[connection_id]["user_info"] == user_info
        
        # Verify welcome message was sent
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_websocket(self, manager, mock_websocket):
        """Test WebSocket disconnection."""
        connection_id = "test-connection-1"
        user_info = {"user_id": "test-user", "role": "faculty"}
        
        # First connect
        await manager.connect(mock_websocket, connection_id, user_info)
        
        # Then disconnect
        await manager.disconnect(connection_id)
        
        # Verify connection was removed
        assert connection_id not in manager.active_connections
        assert connection_id not in manager.connection_metadata
        assert connection_id not in manager.last_heartbeat
    
    @pytest.mark.asyncio
    async def test_session_subscription(self, manager, mock_websocket):
        """Test session subscription functionality."""
        connection_id = "test-connection-1"
        session_id = "test-session-1"
        user_info = {"user_id": "test-user", "role": "faculty"}
        
        # Connect first
        await manager.connect(mock_websocket, connection_id, user_info)
        
        # Subscribe to session
        await manager.subscribe_to_session(connection_id, session_id)
        
        # Verify subscription
        assert session_id in manager.session_subscriptions
        assert connection_id in manager.session_subscriptions[session_id]
        assert session_id in manager.connection_metadata[connection_id]["subscriptions"]
    
    @pytest.mark.asyncio
    async def test_broadcast_to_session(self, manager, mock_websocket):
        """Test broadcasting messages to session subscribers."""
        connection_id = "test-connection-1"
        session_id = "test-session-1"
        user_info = {"user_id": "test-user", "role": "faculty"}
        
        # Connect and subscribe
        await manager.connect(mock_websocket, connection_id, user_info)
        await manager.subscribe_to_session(connection_id, session_id)
        
        # Broadcast message
        test_message = {"type": "test", "data": "test_data"}
        await manager.broadcast_to_session(session_id, test_message)
        
        # Verify message was sent (2 calls: welcome message + broadcast)
        assert mock_websocket.send_text.call_count == 3  # welcome + subscription + broadcast
    
    @pytest.mark.asyncio
    async def test_send_attendance_update(self, manager, mock_websocket):
        """Test sending attendance updates."""
        connection_id = "test-connection-1"
        session_id = "test-session-1"
        user_info = {"user_id": "test-user", "role": "faculty"}
        
        # Connect and subscribe
        await manager.connect(mock_websocket, connection_id, user_info)
        await manager.subscribe_to_session(connection_id, session_id)
        
        # Send attendance update
        attendance_data = {
            "total_registered": 30,
            "total_detected": 25,
            "attendance_percentage": 83.33
        }
        await manager.send_attendance_update(session_id, attendance_data)
        
        # Verify attendance update was sent
        assert mock_websocket.send_text.call_count == 3  # welcome + subscription + attendance


class TestWebSocketIntegrationService:
    """Test cases for WebSocket integration service."""
    
    @pytest.fixture
    def integration_service(self):
        """Create WebSocket integration service for testing."""
        service = WebSocketIntegrationService()
        service._connection_manager = Mock()
        service._connection_manager.send_attendance_update = AsyncMock()
        service._connection_manager.send_emotion_update = AsyncMock()
        service._connection_manager.send_alert = AsyncMock()
        return service
    
    @pytest.fixture
    def sample_attendance_session(self):
        """Create sample attendance session for testing."""
        return AttendanceSession(
            session_id="test-session-1",
            class_id="CS101",
            faculty_id="faculty-001",
            start_time=datetime.utcnow(),
            total_registered=30,
            total_detected=25,
            attendance_records=[
                AttendanceRecord(
                    student_id="student-001",
                    session_id="test-session-1",
                    status=AttendanceStatus.PRESENT,
                    timestamp=datetime.utcnow(),
                    confidence=0.95
                )
            ],
            is_active=True
        )
    
    @pytest.fixture
    def sample_emotion_stats(self):
        """Create sample emotion statistics for testing."""
        return EmotionStatistics(
            session_id="test-session-1",
            total_detections=100,
            emotion_breakdown={
                EmotionType.INTERESTED: 60.0,
                EmotionType.BORED: 25.0,
                EmotionType.CONFUSED: 15.0
            },
            engagement_score=7.5,
            average_engagement=7.2,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )
    
    @pytest.mark.asyncio
    async def test_broadcast_attendance_update(self, integration_service, sample_attendance_session):
        """Test broadcasting attendance updates."""
        await integration_service.broadcast_attendance_update(sample_attendance_session)
        
        # Verify attendance update was called
        integration_service._connection_manager.send_attendance_update.assert_called_once()
        
        # Check the call arguments
        call_args = integration_service._connection_manager.send_attendance_update.call_args
        session_id, attendance_data = call_args[0]
        
        assert session_id == "test-session-1"
        assert attendance_data["total_registered"] == 30
        assert attendance_data["total_detected"] == 25
        assert attendance_data["attendance_percentage"] == 83.33
        assert attendance_data["present_count"] == 1
    
    @pytest.mark.asyncio
    async def test_broadcast_emotion_update(self, integration_service, sample_emotion_stats):
        """Test broadcasting emotion updates."""
        session_id = "test-session-1"
        
        await integration_service.broadcast_emotion_update(session_id, sample_emotion_stats)
        
        # Verify emotion update was called
        integration_service._connection_manager.send_emotion_update.assert_called_once()
        
        # Check the call arguments
        call_args = integration_service._connection_manager.send_emotion_update.call_args
        called_session_id, emotion_data = call_args[0]
        
        assert called_session_id == session_id
        assert emotion_data["total_detections"] == 100
        assert emotion_data["engagement_score"] == 7.5
        assert EmotionType.INTERESTED in emotion_data["emotion_breakdown"]
    
    @pytest.mark.asyncio
    async def test_broadcast_validation_alert(self, integration_service):
        """Test broadcasting validation alerts."""
        session_id = "test-session-1"
        alert_data = {
            "type": "attendance_discrepancy",
            "severity": "warning",
            "title": "Attendance Count Mismatch",
            "message": "Expected 30 students, detected 25",
            "requires_action": True
        }
        
        await integration_service.broadcast_validation_alert(session_id, alert_data)
        
        # Verify alert was sent
        integration_service._connection_manager.send_alert.assert_called_once()
        
        # Check the call arguments
        call_args = integration_service._connection_manager.send_alert.call_args
        alert_message, called_session_id = call_args[0]
        
        assert called_session_id == session_id
        assert alert_message["alert_type"] == "attendance_discrepancy"
        assert alert_message["severity"] == "warning"
        assert alert_message["requires_action"] is True
    
    @pytest.mark.asyncio
    async def test_disabled_service(self, integration_service, sample_attendance_session):
        """Test that disabled service doesn't broadcast."""
        integration_service.disable()
        
        await integration_service.broadcast_attendance_update(sample_attendance_session)
        
        # Verify no calls were made
        integration_service._connection_manager.send_attendance_update.assert_not_called()
    
    def test_connection_stats(self, integration_service):
        """Test getting connection statistics."""
        integration_service._connection_manager.get_connection_count = Mock(return_value=5)
        integration_service._connection_manager.session_subscriptions = {
            "session-1": {"conn-1", "conn-2"},
            "session-2": {"conn-3"}
        }
        integration_service._connection_manager.get_session_subscriber_count = Mock(side_effect=lambda s: len(integration_service._connection_manager.session_subscriptions.get(s, set())))
        
        stats = integration_service.get_connection_stats()
        
        assert stats["total_connections"] == 5
        assert stats["session_subscriptions"]["session-1"] == 2
        assert stats["session_subscriptions"]["session-2"] == 1
        assert stats["enabled"] is True


class TestWebSocketEndpoints:
    """Test WebSocket endpoints integration."""
    
    @pytest.mark.asyncio
    async def test_websocket_status_endpoint(self):
        """Test WebSocket status endpoint."""
        # This would require a full FastAPI test setup
        # For now, we'll test the connection manager directly
        manager = ConnectionManager()
        
        # Mock some connections
        manager.active_connections = {"conn-1": Mock(), "conn-2": Mock()}
        manager.session_subscriptions = {"session-1": {"conn-1"}}
        manager.connection_metadata = {
            "conn-1": {
                "user_info": {"user_id": "user-1", "role": "faculty"},
                "connected_at": datetime.utcnow(),
                "subscriptions": {"session-1"}
            }
        }
        manager.last_heartbeat = {"conn-1": datetime.utcnow()}
        
        # Test status information
        assert manager.get_connection_count() == 2
        assert manager.get_session_subscriber_count("session-1") == 1
        
        connection_info = manager.get_connection_info()
        assert len(connection_info) == 1
        assert connection_info[0]["user_info"]["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_websocket_integration_with_attendance_service():
    """Test WebSocket integration with attendance service."""
    # Mock the WebSocket integration
    with patch('backend.services.websocket_integration_service.get_websocket_integration') as mock_get_integration:
        mock_integration = Mock()
        mock_integration.broadcast_attendance_update = AsyncMock()
        mock_get_integration.return_value = mock_integration
        
        # Import after patching
        from backend.services.attendance_service import AttendanceService
        
        # Create mock dependencies
        attendance_repo = Mock()
        student_repo = Mock()
        face_detection_repo = Mock()
        face_recognition_service = Mock()
        
        # Create service instance
        service = AttendanceService(
            attendance_repo=attendance_repo,
            student_repo=student_repo,
            face_detection_repo=face_detection_repo,
            face_recognition_service=face_recognition_service
        )
        
        # Verify WebSocket integration was initialized
        assert service.websocket_integration == mock_integration


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
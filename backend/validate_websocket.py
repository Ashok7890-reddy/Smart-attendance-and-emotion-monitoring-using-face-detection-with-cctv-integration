"""
Simple validation script for WebSocket functionality.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages = []
        self.closed = False
    
    async def accept(self):
        """Mock accept method."""
        pass
    
    async def send_text(self, message: str):
        """Mock send_text method."""
        self.messages.append(message)
    
    async def close(self):
        """Mock close method."""
        self.closed = True


class SimpleConnectionManager:
    """Simplified connection manager for validation."""
    
    def __init__(self):
        self.active_connections = {}
        self.session_subscriptions = {}
        self.connection_metadata = {}
    
    async def connect(self, websocket, connection_id: str, user_info: Dict[str, Any]):
        """Connect a WebSocket."""
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "user_info": user_info,
            "connected_at": datetime.utcnow(),
            "subscriptions": set()
        }
        
        # Send welcome message
        welcome_message = {
            "type": "connection_established",
            "connection_id": connection_id,
            "message": "Connected to Smart Attendance System",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(welcome_message, default=str))
    
    async def subscribe_to_session(self, connection_id: str, session_id: str):
        """Subscribe connection to session."""
        if session_id not in self.session_subscriptions:
            self.session_subscriptions[session_id] = set()
        
        self.session_subscriptions[session_id].add(connection_id)
        self.connection_metadata[connection_id]["subscriptions"].add(session_id)
        
        # Send confirmation
        websocket = self.active_connections[connection_id]
        confirmation = {
            "type": "subscription_confirmed",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(confirmation, default=str))
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcast message to session subscribers."""
        if session_id in self.session_subscriptions:
            for connection_id in self.session_subscriptions[session_id]:
                if connection_id in self.active_connections:
                    websocket = self.active_connections[connection_id]
                    await websocket.send_text(json.dumps(message, default=str))
    
    async def send_attendance_update(self, session_id: str, attendance_data: Dict[str, Any]):
        """Send attendance update."""
        message = {
            "type": "attendance_update",
            "session_id": session_id,
            "data": attendance_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_session(session_id, message)
    
    async def send_emotion_update(self, session_id: str, emotion_data: Dict[str, Any]):
        """Send emotion update."""
        message = {
            "type": "emotion_update",
            "session_id": session_id,
            "data": emotion_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_session(session_id, message)


async def test_websocket_functionality():
    """Test WebSocket functionality."""
    print("Testing WebSocket functionality...")
    
    # Create manager and mock WebSocket
    manager = SimpleConnectionManager()
    websocket = MockWebSocket()
    
    # Test connection
    connection_id = "test-connection-1"
    user_info = {"user_id": "faculty-001", "role": "faculty"}
    
    await manager.connect(websocket, connection_id, user_info)
    print(f"✓ Connection established for {connection_id}")
    
    # Test session subscription
    session_id = "test-session-1"
    await manager.subscribe_to_session(connection_id, session_id)
    print(f"✓ Subscribed to session {session_id}")
    
    # Test attendance update
    attendance_data = {
        "total_registered": 30,
        "total_detected": 25,
        "attendance_percentage": 83.33,
        "present_students": [
            {"student_id": "student-001", "confidence": 0.95}
        ]
    }
    await manager.send_attendance_update(session_id, attendance_data)
    print("✓ Attendance update sent")
    
    # Test emotion update
    emotion_data = {
        "total_detections": 100,
        "emotion_breakdown": {
            "interested": 60.0,
            "bored": 25.0,
            "confused": 15.0
        },
        "engagement_score": 7.5
    }
    await manager.send_emotion_update(session_id, emotion_data)
    print("✓ Emotion update sent")
    
    # Verify messages were sent
    print(f"\nTotal messages sent: {len(websocket.messages)}")
    for i, message in enumerate(websocket.messages):
        data = json.loads(message)
        print(f"Message {i+1}: {data['type']}")
    
    # Verify subscription tracking
    assert connection_id in manager.session_subscriptions[session_id]
    assert session_id in manager.connection_metadata[connection_id]["subscriptions"]
    print("✓ Subscription tracking verified")
    
    print("\n🎉 All WebSocket functionality tests passed!")


async def test_multiple_connections():
    """Test multiple WebSocket connections."""
    print("\nTesting multiple connections...")
    
    manager = SimpleConnectionManager()
    
    # Create multiple connections
    connections = []
    for i in range(3):
        websocket = MockWebSocket()
        connection_id = f"test-connection-{i+1}"
        user_info = {"user_id": f"user-{i+1}", "role": "faculty"}
        
        await manager.connect(websocket, connection_id, user_info)
        await manager.subscribe_to_session(connection_id, "shared-session")
        connections.append((connection_id, websocket))
    
    print(f"✓ Created {len(connections)} connections")
    
    # Broadcast to all
    test_message = {
        "type": "test_broadcast",
        "message": "Hello all subscribers!"
    }
    await manager.broadcast_to_session("shared-session", test_message)
    
    # Verify all received the message
    for connection_id, websocket in connections:
        # Each should have 2 messages: welcome + subscription + broadcast
        assert len(websocket.messages) == 3
        last_message = json.loads(websocket.messages[-1])
        assert last_message["type"] == "test_broadcast"
    
    print("✓ Broadcast to multiple connections verified")


if __name__ == "__main__":
    asyncio.run(test_websocket_functionality())
    asyncio.run(test_multiple_connections())
    print("\n✅ All WebSocket validation tests completed successfully!")
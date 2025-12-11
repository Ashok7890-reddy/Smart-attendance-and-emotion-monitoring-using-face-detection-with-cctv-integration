"""
WebSocket server for real-time updates.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, List, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.routing import APIRouter
import asyncio
from uuid import uuid4

from .dependencies import get_attendance_service, get_config
from .schemas import (
    WebSocketMessage, AttendanceUpdateMessage, EmotionUpdateMessage, AlertMessage
)
from ..services.attendance_service import AttendanceService
from ..core.config import Config

logger = logging.getLogger(__name__)

# WebSocket router
websocket_router = APIRouter()


class ConnectionManager:
    """
    WebSocket connection manager for handling multiple client connections.
    
    Requirements: 3.5, 5.2, 5.3
    - Create WebSocket connections for real-time dashboard updates
    - Implement real-time attendance and emotion statistics broadcasting
    - Set up connection management and error handling
    """
    
    def __init__(self):
        # Active connections by connection ID
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Subscriptions by session ID
        self.session_subscriptions: Dict[str, Set[str]] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Heartbeat tracking
        self.last_heartbeat: Dict[str, datetime] = {}
        
        # Background task for cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_stale_connections())
    
    async def _cleanup_stale_connections(self):
        """Clean up stale connections periodically."""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                current_time = datetime.utcnow()
                stale_connections = []
                
                for connection_id, last_heartbeat in self.last_heartbeat.items():
                    if current_time - last_heartbeat > timedelta(minutes=5):
                        stale_connections.append(connection_id)
                
                for connection_id in stale_connections:
                    await self.disconnect(connection_id)
                    logger.info(f"Cleaned up stale connection: {connection_id}")
                    
            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}")
    
    async def connect(self, websocket: WebSocket, connection_id: str, user_info: Dict[str, Any]):
        """Accept a new WebSocket connection."""
        try:
            await websocket.accept()
            
            self.active_connections[connection_id] = websocket
            self.connection_metadata[connection_id] = {
                "user_info": user_info,
                "connected_at": datetime.utcnow(),
                "subscriptions": set()
            }
            self.last_heartbeat[connection_id] = datetime.utcnow()
            
            logger.info(f"WebSocket connection established: {connection_id}")
            
            # Send welcome message
            await self.send_personal_message(connection_id, {
                "type": "connection_established",
                "connection_id": connection_id,
                "message": "Connected to Smart Attendance System",
                "timestamp": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {str(e)}")
            raise HTTPException(status_code=500, detail="Connection failed")
    
    async def disconnect(self, connection_id: str):
        """Disconnect a WebSocket connection."""
        try:
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                
                # Remove from session subscriptions
                for session_id, subscribers in self.session_subscriptions.items():
                    subscribers.discard(connection_id)
                
                # Clean up empty subscriptions
                empty_sessions = [
                    session_id for session_id, subscribers in self.session_subscriptions.items()
                    if not subscribers
                ]
                for session_id in empty_sessions:
                    del self.session_subscriptions[session_id]
                
                # Remove connection data
                del self.active_connections[connection_id]
                self.connection_metadata.pop(connection_id, None)
                self.last_heartbeat.pop(connection_id, None)
                
                logger.info(f"WebSocket connection disconnected: {connection_id}")
                
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {str(e)}")
    
    async def send_personal_message(self, connection_id: str, message: Dict[str, Any]):
        """Send a message to a specific connection."""
        try:
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message, default=str))
                self.last_heartbeat[connection_id] = datetime.utcnow()
                
        except WebSocketDisconnect:
            await self.disconnect(connection_id)
        except Exception as e:
            logger.error(f"Failed to send message to {connection_id}: {str(e)}")
            await self.disconnect(connection_id)
    
    async def subscribe_to_session(self, connection_id: str, session_id: str):
        """Subscribe a connection to session updates."""
        try:
            if connection_id in self.active_connections:
                if session_id not in self.session_subscriptions:
                    self.session_subscriptions[session_id] = set()
                
                self.session_subscriptions[session_id].add(connection_id)
                self.connection_metadata[connection_id]["subscriptions"].add(session_id)
                
                await self.send_personal_message(connection_id, {
                    "type": "subscription_confirmed",
                    "session_id": session_id,
                    "message": f"Subscribed to session {session_id}",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                logger.info(f"Connection {connection_id} subscribed to session {session_id}")
                
        except Exception as e:
            logger.error(f"Failed to subscribe connection to session: {str(e)}")
    
    async def unsubscribe_from_session(self, connection_id: str, session_id: str):
        """Unsubscribe a connection from session updates."""
        try:
            if session_id in self.session_subscriptions:
                self.session_subscriptions[session_id].discard(connection_id)
                
                if not self.session_subscriptions[session_id]:
                    del self.session_subscriptions[session_id]
            
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["subscriptions"].discard(session_id)
            
            await self.send_personal_message(connection_id, {
                "type": "unsubscription_confirmed",
                "session_id": session_id,
                "message": f"Unsubscribed from session {session_id}",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            logger.info(f"Connection {connection_id} unsubscribed from session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to unsubscribe connection from session: {str(e)}")
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """Broadcast a message to all connections subscribed to a session."""
        try:
            if session_id in self.session_subscriptions:
                subscribers = self.session_subscriptions[session_id].copy()
                disconnected_connections = []
                
                for connection_id in subscribers:
                    try:
                        await self.send_personal_message(connection_id, message)
                    except Exception as e:
                        logger.error(f"Failed to send to {connection_id}: {str(e)}")
                        disconnected_connections.append(connection_id)
                
                # Clean up disconnected connections
                for connection_id in disconnected_connections:
                    await self.disconnect(connection_id)
                
                logger.debug(f"Broadcasted message to {len(subscribers)} subscribers of session {session_id}")
                
        except Exception as e:
            logger.error(f"Failed to broadcast to session {session_id}: {str(e)}")
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast a message to all active connections."""
        try:
            connections = list(self.active_connections.keys())
            disconnected_connections = []
            
            for connection_id in connections:
                try:
                    await self.send_personal_message(connection_id, message)
                except Exception as e:
                    logger.error(f"Failed to send to {connection_id}: {str(e)}")
                    disconnected_connections.append(connection_id)
            
            # Clean up disconnected connections
            for connection_id in disconnected_connections:
                await self.disconnect(connection_id)
            
            logger.debug(f"Broadcasted message to {len(connections)} connections")
            
        except Exception as e:
            logger.error(f"Failed to broadcast to all connections: {str(e)}")
    
    async def send_attendance_update(self, session_id: str, attendance_data: Dict[str, Any]):
        """Send attendance update to session subscribers."""
        message = {
            "type": "attendance_update",
            "session_id": session_id,
            "data": attendance_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_session(session_id, message)
    
    async def send_emotion_update(self, session_id: str, emotion_data: Dict[str, Any]):
        """Send emotion statistics update to session subscribers."""
        message = {
            "type": "emotion_update",
            "session_id": session_id,
            "data": emotion_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_session(session_id, message)
    
    async def send_alert(self, alert_data: Dict[str, Any], session_id: Optional[str] = None):
        """Send alert message to relevant connections."""
        message = {
            "type": "alert",
            "data": alert_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if session_id:
            await self.broadcast_to_session(session_id, message)
        else:
            await self.broadcast_to_all(message)
    
    async def send_system_status(self, status_data: Dict[str, Any]):
        """Send system status update to all connections."""
        message = {
            "type": "system_status",
            "data": status_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_all(message)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_session_subscriber_count(self, session_id: str) -> int:
        """Get the number of subscribers for a session."""
        return len(self.session_subscriptions.get(session_id, set()))
    
    def get_connection_info(self) -> List[Dict[str, Any]]:
        """Get information about all active connections."""
        info = []
        for connection_id, metadata in self.connection_metadata.items():
            info.append({
                "connection_id": connection_id,
                "user_info": metadata.get("user_info", {}),
                "connected_at": metadata.get("connected_at").isoformat() if metadata.get("connected_at") else None,
                "subscriptions": list(metadata.get("subscriptions", set())),
                "last_heartbeat": self.last_heartbeat.get(connection_id).isoformat() if connection_id in self.last_heartbeat else None
            })
        return info


# Global connection manager instance
connection_manager = ConnectionManager()


@websocket_router.websocket("/ws/{connection_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    connection_id: str,
    user_id: Optional[str] = None,
    role: Optional[str] = None
):
    """
    WebSocket endpoint for real-time updates.
    
    Requirements: 3.5, 5.2, 5.3
    - Create WebSocket connections for real-time dashboard updates
    - Implement real-time attendance and emotion statistics broadcasting
    - Set up connection management and error handling
    """
    user_info = {
        "user_id": user_id or "anonymous",
        "role": role or "guest"
    }
    
    await connection_manager.connect(websocket, connection_id, user_info)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                # Handle different message types
                if message_type == "ping":
                    await connection_manager.send_personal_message(connection_id, {
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                elif message_type == "subscribe":
                    session_id = message.get("session_id")
                    if session_id:
                        await connection_manager.subscribe_to_session(connection_id, session_id)
                    else:
                        await connection_manager.send_personal_message(connection_id, {
                            "type": "error",
                            "message": "session_id required for subscription"
                        })
                
                elif message_type == "unsubscribe":
                    session_id = message.get("session_id")
                    if session_id:
                        await connection_manager.unsubscribe_from_session(connection_id, session_id)
                    else:
                        await connection_manager.send_personal_message(connection_id, {
                            "type": "error",
                            "message": "session_id required for unsubscription"
                        })
                
                elif message_type == "get_status":
                    # Send current connection status
                    await connection_manager.send_personal_message(connection_id, {
                        "type": "status",
                        "connection_id": connection_id,
                        "active_connections": connection_manager.get_connection_count(),
                        "subscriptions": list(connection_manager.connection_metadata[connection_id]["subscriptions"]),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                
                else:
                    await connection_manager.send_personal_message(connection_id, {
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
                    
            except json.JSONDecodeError:
                await connection_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Invalid JSON message"
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await connection_manager.send_personal_message(connection_id, {
                    "type": "error",
                    "message": "Internal server error"
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {str(e)}")
    finally:
        await connection_manager.disconnect(connection_id)


# Helper functions for service integration
async def broadcast_attendance_update(session_id: str, attendance_data: Dict[str, Any]):
    """Broadcast attendance update to WebSocket clients."""
    await connection_manager.send_attendance_update(session_id, attendance_data)


async def broadcast_emotion_update(session_id: str, emotion_data: Dict[str, Any]):
    """Broadcast emotion statistics update to WebSocket clients."""
    await connection_manager.send_emotion_update(session_id, emotion_data)


async def broadcast_alert(alert_data: Dict[str, Any], session_id: Optional[str] = None):
    """Broadcast alert to WebSocket clients."""
    await connection_manager.send_alert(alert_data, session_id)


async def broadcast_system_status(status_data: Dict[str, Any]):
    """Broadcast system status to WebSocket clients."""
    await connection_manager.send_system_status(status_data)


# WebSocket status endpoint
@websocket_router.get("/ws/status")
async def websocket_status():
    """Get WebSocket server status."""
    return {
        "active_connections": connection_manager.get_connection_count(),
        "session_subscriptions": {
            session_id: len(subscribers) 
            for session_id, subscribers in connection_manager.session_subscriptions.items()
        },
        "connection_info": connection_manager.get_connection_info(),
        "timestamp": datetime.utcnow().isoformat()
    }
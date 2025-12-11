"""
WebSocket server for real-time notifications in the Smart Attendance System.
Handles real-time delivery of alerts and notifications to connected clients.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Set, Dict, List
import websockets
from websockets.server import WebSocketServerProtocol

from backend.services.notification_service import NotificationMessage, NotificationPriority


class WebSocketNotificationServer:
    """
    WebSocket server for real-time notification delivery.
    
    Requirements: 7.1, 7.2 - Real-time alert system and notification delivery
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.connected_clients: Set[WebSocketServerProtocol] = set()
        self.client_subscriptions: Dict[WebSocketServerProtocol, Dict] = {}
        self.logger = logging.getLogger(__name__)
        self.server = None
    
    async def start_server(self):
        """Start the WebSocket server."""
        try:
            self.server = await websockets.serve(
                self.handle_client_connection,
                self.host,
                self.port
            )
            self.logger.info(f"WebSocket notification server started on {self.host}:{self.port}")
            
            # Keep the server running
            await self.server.wait_closed()
            
        except Exception as e:
            self.logger.error(f"Failed to start WebSocket server: {str(e)}")
            raise
    
    async def stop_server(self):
        """Stop the WebSocket server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.logger.info("WebSocket notification server stopped")
    
    async def handle_client_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new client connection."""
        try:
            self.connected_clients.add(websocket)
            self.client_subscriptions[websocket] = {
                "user_id": None,
                "role": None,
                "subscribed_types": [],
                "connected_at": datetime.now()
            }
            
            self.logger.info(f"New WebSocket client connected from {websocket.remote_address}")
            
            # Send welcome message
            await self.send_to_client(websocket, {
                "type": "connection_established",
                "message": "Connected to notification server",
                "timestamp": datetime.now().isoformat()
            })
            
            # Handle incoming messages
            async for message in websocket:
                await self.handle_client_message(websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"Client {websocket.remote_address} disconnected")
        except Exception as e:
            self.logger.error(f"Error handling client connection: {str(e)}")
        finally:
            # Clean up client
            self.connected_clients.discard(websocket)
            self.client_subscriptions.pop(websocket, None)
    
    async def handle_client_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle incoming message from client."""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type == "authenticate":
                await self.handle_authentication(websocket, data)
            elif message_type == "subscribe":
                await self.handle_subscription(websocket, data)
            elif message_type == "acknowledge":
                await self.handle_acknowledgment(websocket, data)
            elif message_type == "ping":
                await self.send_to_client(websocket, {"type": "pong", "timestamp": datetime.now().isoformat()})
            else:
                await self.send_to_client(websocket, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                })
                
        except json.JSONDecodeError:
            await self.send_to_client(websocket, {
                "type": "error",
                "message": "Invalid JSON message"
            })
        except Exception as e:
            self.logger.error(f"Error handling client message: {str(e)}")
            await self.send_to_client(websocket, {
                "type": "error",
                "message": "Internal server error"
            })
    
    async def handle_authentication(self, websocket: WebSocketServerProtocol, data: Dict):
        """Handle client authentication."""
        try:
            user_id = data.get("user_id")
            role = data.get("role")
            
            if user_id and role:
                self.client_subscriptions[websocket]["user_id"] = user_id
                self.client_subscriptions[websocket]["role"] = role
                
                await self.send_to_client(websocket, {
                    "type": "authentication_success",
                    "message": f"Authenticated as {role}",
                    "user_id": user_id
                })
                
                self.logger.info(f"Client authenticated: {user_id} ({role})")
            else:
                await self.send_to_client(websocket, {
                    "type": "authentication_failed",
                    "message": "Missing user_id or role"
                })
                
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            await self.send_to_client(websocket, {
                "type": "authentication_failed",
                "message": "Authentication failed"
            })
    
    async def handle_subscription(self, websocket: WebSocketServerProtocol, data: Dict):
        """Handle client subscription to notification types."""
        try:
            notification_types = data.get("notification_types", [])
            
            if notification_types:
                self.client_subscriptions[websocket]["subscribed_types"] = notification_types
                
                await self.send_to_client(websocket, {
                    "type": "subscription_success",
                    "message": f"Subscribed to {len(notification_types)} notification types",
                    "subscribed_types": notification_types
                })
                
                self.logger.info(f"Client subscribed to: {notification_types}")
            else:
                await self.send_to_client(websocket, {
                    "type": "subscription_failed",
                    "message": "No notification types specified"
                })
                
        except Exception as e:
            self.logger.error(f"Subscription error: {str(e)}")
            await self.send_to_client(websocket, {
                "type": "subscription_failed",
                "message": "Subscription failed"
            })
    
    async def handle_acknowledgment(self, websocket: WebSocketServerProtocol, data: Dict):
        """Handle notification acknowledgment from client."""
        try:
            message_id = data.get("message_id")
            user_id = self.client_subscriptions[websocket].get("user_id")
            
            if message_id and user_id:
                # In a real implementation, this would call the notification service
                # to record the acknowledgment
                await self.send_to_client(websocket, {
                    "type": "acknowledgment_received",
                    "message_id": message_id,
                    "timestamp": datetime.now().isoformat()
                })
                
                self.logger.info(f"Acknowledgment received from {user_id} for message {message_id}")
            else:
                await self.send_to_client(websocket, {
                    "type": "acknowledgment_failed",
                    "message": "Missing message_id or user not authenticated"
                })
                
        except Exception as e:
            self.logger.error(f"Acknowledgment error: {str(e)}")
            await self.send_to_client(websocket, {
                "type": "acknowledgment_failed",
                "message": "Acknowledgment failed"
            })
    
    async def send_to_client(self, websocket: WebSocketServerProtocol, data: Dict):
        """Send data to a specific client."""
        try:
            message = json.dumps(data, default=str)
            await websocket.send(message)
        except Exception as e:
            self.logger.error(f"Failed to send message to client: {str(e)}")
    
    async def broadcast_notification(self, notification: NotificationMessage):
        """
        Broadcast notification to all relevant connected clients.
        
        Args:
            notification: Notification message to broadcast
        """
        if not self.connected_clients:
            return
        
        try:
            # Prepare notification data
            notification_data = {
                "type": "notification",
                "message_id": notification.message_id,
                "notification_type": notification.type.value,
                "title": notification.title,
                "message": notification.message,
                "priority": notification.priority.value,
                "timestamp": notification.timestamp.isoformat(),
                "requires_acknowledgment": notification.requires_acknowledgment,
                "metadata": notification.metadata
            }
            
            # Send to relevant clients
            disconnected_clients = set()
            
            for websocket in self.connected_clients.copy():
                try:
                    client_info = self.client_subscriptions.get(websocket, {})
                    
                    # Check if client should receive this notification
                    if self._should_send_to_client(client_info, notification):
                        await self.send_to_client(websocket, notification_data)
                        
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(websocket)
                except Exception as e:
                    self.logger.error(f"Failed to send notification to client: {str(e)}")
            
            # Clean up disconnected clients
            for websocket in disconnected_clients:
                self.connected_clients.discard(websocket)
                self.client_subscriptions.pop(websocket, None)
            
            self.logger.info(f"Notification {notification.message_id} broadcast to {len(self.connected_clients)} clients")
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast notification: {str(e)}")
    
    def _should_send_to_client(self, client_info: Dict, notification: NotificationMessage) -> bool:
        """Determine if notification should be sent to client."""
        try:
            # Check if client is authenticated
            if not client_info.get("user_id"):
                return False
            
            # Check role-based filtering
            client_role = client_info.get("role")
            if client_role and client_role not in notification.recipients:
                # Allow if client role matches any recipient
                role_mapping = {
                    "faculty": ["faculty"],
                    "admin": ["admin", "administrator"],
                    "tech_support": ["tech_support", "technical_support"]
                }
                
                allowed_roles = role_mapping.get(client_role, [client_role])
                if not any(role in notification.recipients for role in allowed_roles):
                    return False
            
            # Check subscription filtering
            subscribed_types = client_info.get("subscribed_types", [])
            if subscribed_types and notification.type.value not in subscribed_types:
                # Always send critical notifications regardless of subscription
                if notification.priority != NotificationPriority.CRITICAL:
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking client notification eligibility: {str(e)}")
            return False
    
    async def send_system_status(self, status_data: Dict):
        """Send system status update to all connected clients."""
        try:
            message = {
                "type": "system_status",
                "data": status_data,
                "timestamp": datetime.now().isoformat()
            }
            
            disconnected_clients = set()
            
            for websocket in self.connected_clients.copy():
                try:
                    await self.send_to_client(websocket, message)
                except websockets.exceptions.ConnectionClosed:
                    disconnected_clients.add(websocket)
                except Exception as e:
                    self.logger.error(f"Failed to send status to client: {str(e)}")
            
            # Clean up disconnected clients
            for websocket in disconnected_clients:
                self.connected_clients.discard(websocket)
                self.client_subscriptions.pop(websocket, None)
            
        except Exception as e:
            self.logger.error(f"Failed to send system status: {str(e)}")
    
    def get_connected_clients_info(self) -> List[Dict]:
        """Get information about connected clients."""
        try:
            clients_info = []
            
            for websocket, client_info in self.client_subscriptions.items():
                if websocket in self.connected_clients:
                    clients_info.append({
                        "remote_address": str(websocket.remote_address),
                        "user_id": client_info.get("user_id"),
                        "role": client_info.get("role"),
                        "subscribed_types": client_info.get("subscribed_types", []),
                        "connected_at": client_info.get("connected_at").isoformat() if client_info.get("connected_at") else None
                    })
            
            return clients_info
            
        except Exception as e:
            self.logger.error(f"Failed to get client info: {str(e)}")
            return []
    
    def get_server_statistics(self) -> Dict:
        """Get WebSocket server statistics."""
        try:
            return {
                "connected_clients": len(self.connected_clients),
                "authenticated_clients": len([
                    c for c in self.client_subscriptions.values() 
                    if c.get("user_id")
                ]),
                "server_host": self.host,
                "server_port": self.port,
                "server_running": self.server is not None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get server statistics: {str(e)}")
            return {"error": str(e)}


# Singleton instance for global access
websocket_server = WebSocketNotificationServer()


async def start_notification_server(host: str = "localhost", port: int = 8765):
    """Start the WebSocket notification server."""
    global websocket_server
    websocket_server = WebSocketNotificationServer(host, port)
    await websocket_server.start_server()


if __name__ == "__main__":
    # Run the server
    asyncio.run(start_notification_server())
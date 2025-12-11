"""
Notification integration service for the Smart Attendance System.
Integrates notification service, WebSocket server, and escalation manager.
"""

import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from backend.services.notification_service import NotificationService, NotificationMessage
from backend.services.websocket_notification_server import WebSocketNotificationServer
from backend.services.alert_escalation_manager import AlertEscalationManager


class NotificationIntegrationService:
    """
    Integrates all notification components for comprehensive alert management.
    
    Requirements: 7.1, 7.2, 7.3 - Complete notification and alerting system
    """
    
    def __init__(self, config=None):
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Initialize core services
        self.notification_service = NotificationService(config)
        self.websocket_server = WebSocketNotificationServer(
            host=self.config.get('websocket_host', 'localhost'),
            port=self.config.get('websocket_port', 8765)
        )
        self.escalation_manager = AlertEscalationManager(self.notification_service)
        
        # Integration state
        self.is_running = False
        self.background_tasks = []
        
        # Setup integrations
        self._setup_integrations()
    
    def _setup_integrations(self):
        """Setup integrations between services."""
        try:
            # Register escalation callbacks
            self.escalation_manager.register_escalation_callback(
                self._handle_escalation_event
            )
            
            # Override notification service's WebSocket handler to use our server
            self.notification_service._send_websocket_notification = self._send_websocket_notification
            
            self.logger.info("Notification service integrations setup complete")
            
        except Exception as e:
            self.logger.error(f"Failed to setup integrations: {str(e)}")
    
    async def start_services(self):
        """Start all notification services."""
        try:
            self.is_running = True
            
            # Start WebSocket server
            websocket_task = asyncio.create_task(
                self.websocket_server.start_server()
            )
            self.background_tasks.append(websocket_task)
            
            # Start background monitoring tasks
            monitoring_task = asyncio.create_task(
                self._background_monitoring()
            )
            self.background_tasks.append(monitoring_task)
            
            self.logger.info("All notification services started successfully")
            
            # Wait for tasks to complete
            await asyncio.gather(*self.background_tasks)
            
        except Exception as e:
            self.logger.error(f"Failed to start notification services: {str(e)}")
            raise
    
    async def stop_services(self):
        """Stop all notification services."""
        try:
            self.is_running = False
            
            # Stop WebSocket server
            await self.websocket_server.stop_server()
            
            # Cancel background tasks
            for task in self.background_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
            
            self.logger.info("All notification services stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping notification services: {str(e)}")
    
    async def _background_monitoring(self):
        """Background monitoring and processing."""
        while self.is_running:
            try:
                # Check for pending escalations
                self.escalation_manager.check_pending_escalations()
                
                # Process any pending notifications
                await self._process_pending_notifications()
                
                # Clean up old data periodically
                if datetime.now().minute == 0:  # Every hour
                    self._cleanup_old_data()
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in background monitoring: {str(e)}")
                await asyncio.sleep(60)
    
    async def _process_pending_notifications(self):
        """Process pending notifications and send via WebSocket."""
        try:
            pending_notifications = self.notification_service.get_pending_notifications()
            
            for notification in pending_notifications:
                # Send via WebSocket
                await self.websocket_server.broadcast_notification(notification)
                
                # Register for escalation if required
                if notification.requires_acknowledgment:
                    self.escalation_manager.register_notification_for_escalation(notification)
                
                # Mark as processed
                self.notification_service.mark_notification_sent(notification.message_id)
            
        except Exception as e:
            self.logger.error(f"Error processing pending notifications: {str(e)}")
    
    def _send_websocket_notification(self, notification: NotificationMessage) -> bool:
        """Enhanced WebSocket notification handler."""
        try:
            # Use asyncio to send via WebSocket server
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Schedule the coroutine
                asyncio.create_task(
                    self.websocket_server.broadcast_notification(notification)
                )
            else:
                # Run in new event loop
                asyncio.run(
                    self.websocket_server.broadcast_notification(notification)
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send WebSocket notification: {str(e)}")
            return False
    
    def _handle_escalation_event(self, event_type: str, escalation_entry: Dict):
        """Handle escalation events."""
        try:
            message_id = escalation_entry["notification"].message_id
            
            if event_type == "escalated":
                self.logger.warning(f"Escalation triggered for notification {message_id}")
                
                # Send system status update
                asyncio.create_task(
                    self.websocket_server.send_system_status({
                        "type": "escalation_triggered",
                        "message_id": message_id,
                        "escalation_level": escalation_entry["current_level"].value,
                        "timestamp": datetime.now().isoformat()
                    })
                )
                
            elif event_type == "acknowledged":
                self.logger.info(f"Escalation acknowledged for notification {message_id}")
                
            elif event_type == "max_escalation_reached":
                self.logger.critical(f"Maximum escalation reached for notification {message_id}")
                
                # Send critical system alert
                asyncio.create_task(
                    self.websocket_server.send_system_status({
                        "type": "max_escalation_reached",
                        "message_id": message_id,
                        "timestamp": datetime.now().isoformat()
                    })
                )
            
        except Exception as e:
            self.logger.error(f"Error handling escalation event: {str(e)}")
    
    def _cleanup_old_data(self):
        """Clean up old notifications and escalations."""
        try:
            # Clean up old notifications
            cleared_notifications = self.notification_service.clear_old_notifications(days=7)
            
            # Clean up old escalations
            cleared_escalations = self.escalation_manager.cleanup_old_escalations(days=7)
            
            if cleared_notifications > 0 or cleared_escalations > 0:
                self.logger.info(
                    f"Cleanup completed: {cleared_notifications} notifications, "
                    f"{cleared_escalations} escalations"
                )
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
    
    # Public API methods
    
    def send_attendance_alert(self, session_id: str, missing_count: int, 
                            missing_students: List[str] = None) -> bool:
        """Send attendance alert through integrated system."""
        return self.notification_service.send_attendance_alert(
            session_id, missing_count, missing_students
        )
    
    def send_camera_connectivity_alert(self, camera_id: str, is_connected: bool) -> bool:
        """Send camera connectivity alert through integrated system."""
        return self.notification_service.send_camera_connectivity_alert(
            camera_id, is_connected
        )
    
    def send_face_recognition_confidence_alert(self, session_id: str, 
                                             low_confidence_count: int,
                                             average_confidence: float) -> bool:
        """Send face recognition confidence alert through integrated system."""
        return self.notification_service.send_face_recognition_confidence_alert(
            session_id, low_confidence_count, average_confidence
        )
    
    def send_performance_alert(self, component: str, processing_time: float) -> bool:
        """Send performance alert through integrated system."""
        return self.notification_service.send_performance_alert(
            component, processing_time
        )
    
    def acknowledge_notification(self, message_id: str, recipient_id: str) -> bool:
        """Acknowledge notification through integrated system."""
        # Acknowledge in both notification service and escalation manager
        notification_ack = self.notification_service.acknowledge_notification(
            message_id, recipient_id
        )
        escalation_ack = self.escalation_manager.acknowledge_notification(
            message_id, recipient_id
        )
        
        return notification_ack or escalation_ack
    
    def get_system_status(self) -> Dict:
        """Get comprehensive system status."""
        try:
            notification_stats = self.notification_service.get_notification_statistics()
            escalation_stats = self.escalation_manager.get_escalation_statistics()
            websocket_stats = self.websocket_server.get_server_statistics()
            
            return {
                "notification_service": notification_stats,
                "escalation_manager": escalation_stats,
                "websocket_server": websocket_stats,
                "integration_status": {
                    "is_running": self.is_running,
                    "background_tasks": len(self.background_tasks),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get system status: {str(e)}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_active_alerts(self) -> Dict:
        """Get all active alerts and escalations."""
        try:
            pending_notifications = self.notification_service.get_pending_notifications()
            unacknowledged_notifications = self.notification_service.get_unacknowledged_notifications()
            active_escalations = self.escalation_manager.get_active_escalations()
            
            return {
                "pending_notifications": [
                    {
                        "message_id": n.message_id,
                        "type": n.type.value,
                        "title": n.title,
                        "priority": n.priority.value,
                        "timestamp": n.timestamp.isoformat(),
                        "recipients": n.recipients
                    }
                    for n in pending_notifications
                ],
                "unacknowledged_notifications": [
                    {
                        "message_id": n.message_id,
                        "type": n.type.value,
                        "title": n.title,
                        "priority": n.priority.value,
                        "timestamp": n.timestamp.isoformat(),
                        "recipients": n.recipients,
                        "acknowledgments": list(n.acknowledgments.keys())
                    }
                    for n in unacknowledged_notifications
                ],
                "active_escalations": active_escalations,
                "summary": {
                    "total_pending": len(pending_notifications),
                    "total_unacknowledged": len(unacknowledged_notifications),
                    "total_escalations": len(active_escalations),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get active alerts: {str(e)}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_connected_clients(self) -> List[Dict]:
        """Get information about connected WebSocket clients."""
        return self.websocket_server.get_connected_clients_info()


# Global instance for easy access
notification_integration = NotificationIntegrationService()


async def start_notification_system(config: Dict = None):
    """Start the complete notification system."""
    global notification_integration
    if config:
        notification_integration = NotificationIntegrationService(config)
    
    await notification_integration.start_services()


async def stop_notification_system():
    """Stop the complete notification system."""
    global notification_integration
    await notification_integration.stop_services()


if __name__ == "__main__":
    # Run the complete notification system
    asyncio.run(start_notification_system())
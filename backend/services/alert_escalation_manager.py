"""
Alert escalation manager for the Smart Attendance System.
Handles escalation workflows and acknowledgment tracking for critical alerts.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from backend.services.notification_service import NotificationMessage, NotificationPriority, NotificationStatus


class EscalationLevel(Enum):
    """Escalation levels."""
    LEVEL_1 = "level_1"  # Initial notification
    LEVEL_2 = "level_2"  # First escalation
    LEVEL_3 = "level_3"  # Second escalation
    LEVEL_4 = "level_4"  # Final escalation


@dataclass
class EscalationRule:
    """Escalation rule configuration."""
    notification_type: str
    priority: NotificationPriority
    escalation_levels: List[Dict]  # List of escalation level configs
    max_escalations: int = 3
    auto_resolve_after_hours: int = 24


class AlertEscalationManager:
    """
    Manages alert escalation workflows and acknowledgment tracking.
    
    Requirements: 7.3 - Alert escalation and acknowledgment workflows
    """
    
    def __init__(self, notification_service=None):
        self.notification_service = notification_service
        self.logger = logging.getLogger(__name__)
        
        # Active escalations tracking
        self.active_escalations: Dict[str, Dict] = {}
        self.escalation_tasks: Dict[str, asyncio.Task] = {}
        
        # Escalation rules configuration
        self.escalation_rules = self._initialize_escalation_rules()
        
        # Callbacks for external integrations
        self.escalation_callbacks: List[Callable] = []
        
        # Start background monitoring
        self._start_background_monitoring()
    
    def _initialize_escalation_rules(self) -> Dict[str, EscalationRule]:
        """Initialize default escalation rules."""
        return {
            "attendance_alert": EscalationRule(
                notification_type="attendance_alert",
                priority=NotificationPriority.HIGH,
                escalation_levels=[
                    {
                        "level": EscalationLevel.LEVEL_1,
                        "delay_minutes": 0,
                        "recipients": ["faculty"],
                        "channels": ["websocket", "dashboard"]
                    },
                    {
                        "level": EscalationLevel.LEVEL_2,
                        "delay_minutes": 15,
                        "recipients": ["faculty", "admin"],
                        "channels": ["websocket", "email", "dashboard"]
                    },
                    {
                        "level": EscalationLevel.LEVEL_3,
                        "delay_minutes": 30,
                        "recipients": ["admin", "tech_support"],
                        "channels": ["email", "sms", "push"]
                    }
                ],
                max_escalations=2,
                auto_resolve_after_hours=4
            ),
            "camera_connectivity": EscalationRule(
                notification_type="camera_connectivity",
                priority=NotificationPriority.CRITICAL,
                escalation_levels=[
                    {
                        "level": EscalationLevel.LEVEL_1,
                        "delay_minutes": 0,
                        "recipients": ["admin", "tech_support"],
                        "channels": ["websocket", "email", "sms"]
                    },
                    {
                        "level": EscalationLevel.LEVEL_2,
                        "delay_minutes": 5,
                        "recipients": ["admin", "tech_support"],
                        "channels": ["email", "sms", "push"]
                    },
                    {
                        "level": EscalationLevel.LEVEL_3,
                        "delay_minutes": 15,
                        "recipients": ["admin", "tech_support"],
                        "channels": ["sms", "push"]
                    }
                ],
                max_escalations=2,
                auto_resolve_after_hours=1
            ),
            "face_recognition_confidence": EscalationRule(
                notification_type="face_recognition_confidence",
                priority=NotificationPriority.HIGH,
                escalation_levels=[
                    {
                        "level": EscalationLevel.LEVEL_1,
                        "delay_minutes": 0,
                        "recipients": ["admin"],
                        "channels": ["websocket", "dashboard"]
                    },
                    {
                        "level": EscalationLevel.LEVEL_2,
                        "delay_minutes": 30,
                        "recipients": ["admin", "tech_support"],
                        "channels": ["email", "dashboard"]
                    }
                ],
                max_escalations=1,
                auto_resolve_after_hours=2
            ),
            "performance_alert": EscalationRule(
                notification_type="performance_alert",
                priority=NotificationPriority.HIGH,
                escalation_levels=[
                    {
                        "level": EscalationLevel.LEVEL_1,
                        "delay_minutes": 0,
                        "recipients": ["tech_support"],
                        "channels": ["websocket", "email"]
                    },
                    {
                        "level": EscalationLevel.LEVEL_2,
                        "delay_minutes": 20,
                        "recipients": ["admin", "tech_support"],
                        "channels": ["email", "sms"]
                    }
                ],
                max_escalations=1,
                auto_resolve_after_hours=2
            ),
            "validation_error": EscalationRule(
                notification_type="validation_error",
                priority=NotificationPriority.HIGH,
                escalation_levels=[
                    {
                        "level": EscalationLevel.LEVEL_1,
                        "delay_minutes": 0,
                        "recipients": ["admin"],
                        "channels": ["websocket", "email"]
                    },
                    {
                        "level": EscalationLevel.LEVEL_2,
                        "delay_minutes": 25,
                        "recipients": ["admin", "tech_support"],
                        "channels": ["email", "sms"]
                    }
                ],
                max_escalations=1,
                auto_resolve_after_hours=3
            )
        }
    
    def _start_background_monitoring(self):
        """Start background monitoring tasks."""
        try:
            # In a real implementation, this would be properly managed
            # For now, we'll handle escalations synchronously when needed
            self.logger.info("Alert escalation manager initialized")
        except Exception as e:
            self.logger.error(f"Failed to start background monitoring: {str(e)}")
    
    def register_notification_for_escalation(self, notification: NotificationMessage) -> bool:
        """
        Register a notification for potential escalation.
        
        Args:
            notification: Notification message to monitor
            
        Returns:
            bool: True if registered successfully
        """
        try:
            # Check if notification requires escalation monitoring
            if not notification.requires_acknowledgment:
                return False
            
            notification_type = notification.type.value
            if notification_type not in self.escalation_rules:
                self.logger.warning(f"No escalation rule found for type: {notification_type}")
                return False
            
            rule = self.escalation_rules[notification_type]
            
            # Create escalation tracking entry
            escalation_entry = {
                "notification": notification,
                "rule": rule,
                "current_level": EscalationLevel.LEVEL_1,
                "escalation_count": 0,
                "created_at": datetime.now(),
                "last_escalation": None,
                "acknowledged": False,
                "resolved": False,
                "acknowledgments": {}
            }
            
            self.active_escalations[notification.message_id] = escalation_entry
            
            # Schedule first escalation check
            self._schedule_escalation_check(notification.message_id)
            
            self.logger.info(f"Registered notification {notification.message_id} for escalation monitoring")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register notification for escalation: {str(e)}")
            return False
    
    def acknowledge_notification(self, message_id: str, recipient_id: str) -> bool:
        """
        Acknowledge a notification and potentially stop escalation.
        
        Args:
            message_id: Notification message ID
            recipient_id: ID of recipient acknowledging
            
        Returns:
            bool: True if acknowledgment was processed
        """
        try:
            if message_id not in self.active_escalations:
                self.logger.warning(f"No active escalation found for message {message_id}")
                return False
            
            escalation_entry = self.active_escalations[message_id]
            escalation_entry["acknowledgments"][recipient_id] = datetime.now()
            
            # Check if sufficient acknowledgments received
            notification = escalation_entry["notification"]
            required_recipients = set(notification.recipients)
            acknowledged_recipients = set(escalation_entry["acknowledgments"].keys())
            
            # Check if all required recipients have acknowledged
            if required_recipients.issubset(acknowledged_recipients):
                escalation_entry["acknowledged"] = True
                escalation_entry["resolved"] = True
                
                # Cancel any pending escalation tasks
                self._cancel_escalation_task(message_id)
                
                self.logger.info(f"Notification {message_id} fully acknowledged - escalation stopped")
                
                # Notify callbacks
                self._trigger_escalation_callbacks("acknowledged", escalation_entry)
                
                return True
            else:
                missing_recipients = required_recipients - acknowledged_recipients
                self.logger.info(f"Partial acknowledgment for {message_id}. Still waiting for: {missing_recipients}")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to process acknowledgment: {str(e)}")
            return False
    
    def _schedule_escalation_check(self, message_id: str):
        """Schedule escalation check for a notification."""
        try:
            if message_id not in self.active_escalations:
                return
            
            escalation_entry = self.active_escalations[message_id]
            rule = escalation_entry["rule"]
            current_level = escalation_entry["current_level"]
            
            # Find next escalation level
            next_level_config = None
            for level_config in rule.escalation_levels:
                if level_config["level"] == current_level:
                    # Find next level
                    current_index = rule.escalation_levels.index(level_config)
                    if current_index + 1 < len(rule.escalation_levels):
                        next_level_config = rule.escalation_levels[current_index + 1]
                    break
            
            if next_level_config:
                delay_minutes = next_level_config["delay_minutes"]
                escalation_time = datetime.now() + timedelta(minutes=delay_minutes)
                
                self.logger.info(f"Escalation scheduled for {message_id} at {escalation_time}")
                
                # In a real implementation, this would use a proper task scheduler
                # For now, we'll track the escalation time
                escalation_entry["next_escalation_time"] = escalation_time
                escalation_entry["next_level_config"] = next_level_config
            
        except Exception as e:
            self.logger.error(f"Failed to schedule escalation check: {str(e)}")
    
    def check_pending_escalations(self):
        """Check for pending escalations that need to be triggered."""
        try:
            current_time = datetime.now()
            
            for message_id, escalation_entry in self.active_escalations.items():
                if (escalation_entry["resolved"] or 
                    escalation_entry["acknowledged"] or
                    escalation_entry["escalation_count"] >= escalation_entry["rule"].max_escalations):
                    continue
                
                next_escalation_time = escalation_entry.get("next_escalation_time")
                if next_escalation_time and current_time >= next_escalation_time:
                    self._trigger_escalation(message_id)
            
        except Exception as e:
            self.logger.error(f"Error checking pending escalations: {str(e)}")
    
    def _trigger_escalation(self, message_id: str):
        """Trigger escalation for a notification."""
        try:
            if message_id not in self.active_escalations:
                return
            
            escalation_entry = self.active_escalations[message_id]
            
            if escalation_entry["resolved"] or escalation_entry["acknowledged"]:
                return
            
            rule = escalation_entry["rule"]
            next_level_config = escalation_entry.get("next_level_config")
            
            if not next_level_config:
                self.logger.warning(f"No next level config for escalation {message_id}")
                return
            
            # Update escalation tracking
            escalation_entry["escalation_count"] += 1
            escalation_entry["current_level"] = next_level_config["level"]
            escalation_entry["last_escalation"] = datetime.now()
            
            # Create escalation notification
            original_notification = escalation_entry["notification"]
            escalation_level = escalation_entry["escalation_count"]
            
            escalation_message = (
                f"ESCALATION LEVEL {escalation_level}: "
                f"Unacknowledged alert - {original_notification.message}"
            )
            
            # Send escalation notification through notification service
            if self.notification_service:
                self.notification_service.send_alert(
                    message=escalation_message,
                    recipients=next_level_config["recipients"],
                    priority=NotificationPriority.CRITICAL,
                    requires_acknowledgment=True
                )
            
            self.logger.critical(f"ESCALATION TRIGGERED: Level {escalation_level} for {message_id}")
            
            # Trigger callbacks
            self._trigger_escalation_callbacks("escalated", escalation_entry)
            
            # Schedule next escalation if not at max level
            if escalation_entry["escalation_count"] < rule.max_escalations:
                self._schedule_escalation_check(message_id)
            else:
                self.logger.warning(f"Maximum escalation level reached for {message_id}")
                escalation_entry["resolved"] = True
                self._trigger_escalation_callbacks("max_escalation_reached", escalation_entry)
            
        except Exception as e:
            self.logger.error(f"Failed to trigger escalation: {str(e)}")
    
    def _cancel_escalation_task(self, message_id: str):
        """Cancel escalation task for a notification."""
        try:
            if message_id in self.escalation_tasks:
                task = self.escalation_tasks[message_id]
                if not task.done():
                    task.cancel()
                del self.escalation_tasks[message_id]
                self.logger.info(f"Cancelled escalation task for {message_id}")
        except Exception as e:
            self.logger.error(f"Failed to cancel escalation task: {str(e)}")
    
    def _trigger_escalation_callbacks(self, event_type: str, escalation_entry: Dict):
        """Trigger registered escalation callbacks."""
        try:
            for callback in self.escalation_callbacks:
                try:
                    callback(event_type, escalation_entry)
                except Exception as e:
                    self.logger.error(f"Escalation callback failed: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed to trigger escalation callbacks: {str(e)}")
    
    def register_escalation_callback(self, callback: Callable):
        """Register a callback for escalation events."""
        self.escalation_callbacks.append(callback)
    
    def get_active_escalations(self) -> List[Dict]:
        """Get list of active escalations."""
        try:
            active_list = []
            
            for message_id, escalation_entry in self.active_escalations.items():
                if not escalation_entry["resolved"]:
                    active_list.append({
                        "message_id": message_id,
                        "notification_type": escalation_entry["notification"].type.value,
                        "current_level": escalation_entry["current_level"].value,
                        "escalation_count": escalation_entry["escalation_count"],
                        "created_at": escalation_entry["created_at"],
                        "last_escalation": escalation_entry["last_escalation"],
                        "acknowledged": escalation_entry["acknowledged"],
                        "acknowledgments": list(escalation_entry["acknowledgments"].keys()),
                        "next_escalation_time": escalation_entry.get("next_escalation_time")
                    })
            
            return active_list
            
        except Exception as e:
            self.logger.error(f"Failed to get active escalations: {str(e)}")
            return []
    
    def get_escalation_statistics(self) -> Dict:
        """Get escalation system statistics."""
        try:
            total_escalations = len(self.active_escalations)
            active_escalations = len([e for e in self.active_escalations.values() if not e["resolved"]])
            acknowledged_escalations = len([e for e in self.active_escalations.values() if e["acknowledged"]])
            
            # Count by type
            type_counts = {}
            for escalation_entry in self.active_escalations.values():
                notification_type = escalation_entry["notification"].type.value
                type_counts[notification_type] = type_counts.get(notification_type, 0) + 1
            
            # Count by escalation level
            level_counts = {}
            for escalation_entry in self.active_escalations.values():
                if not escalation_entry["resolved"]:
                    level = escalation_entry["current_level"].value
                    level_counts[level] = level_counts.get(level, 0) + 1
            
            return {
                "total_escalations": total_escalations,
                "active_escalations": active_escalations,
                "acknowledged_escalations": acknowledged_escalations,
                "acknowledgment_rate": acknowledged_escalations / total_escalations if total_escalations > 0 else 0,
                "type_distribution": type_counts,
                "level_distribution": level_counts,
                "escalation_rules_count": len(self.escalation_rules),
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get escalation statistics: {str(e)}")
            return {"error": str(e), "timestamp": datetime.now()}
    
    def resolve_escalation(self, message_id: str, reason: str = "Manual resolution") -> bool:
        """
        Manually resolve an escalation.
        
        Args:
            message_id: Notification message ID
            reason: Reason for resolution
            
        Returns:
            bool: True if resolved successfully
        """
        try:
            if message_id not in self.active_escalations:
                return False
            
            escalation_entry = self.active_escalations[message_id]
            escalation_entry["resolved"] = True
            escalation_entry["resolution_reason"] = reason
            escalation_entry["resolved_at"] = datetime.now()
            
            # Cancel any pending escalation tasks
            self._cancel_escalation_task(message_id)
            
            self.logger.info(f"Escalation {message_id} manually resolved: {reason}")
            
            # Trigger callbacks
            self._trigger_escalation_callbacks("resolved", escalation_entry)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to resolve escalation: {str(e)}")
            return False
    
    def cleanup_old_escalations(self, days: int = 7) -> int:
        """Clean up old resolved escalations."""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            old_escalations = []
            for message_id, escalation_entry in self.active_escalations.items():
                if (escalation_entry["resolved"] and 
                    escalation_entry["created_at"] < cutoff_date):
                    old_escalations.append(message_id)
            
            for message_id in old_escalations:
                del self.active_escalations[message_id]
                self._cancel_escalation_task(message_id)
            
            self.logger.info(f"Cleaned up {len(old_escalations)} old escalations")
            return len(old_escalations)
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old escalations: {str(e)}")
            return 0
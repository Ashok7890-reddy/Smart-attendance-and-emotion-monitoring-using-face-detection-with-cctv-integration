"""
Real-time system monitoring service for the Smart Attendance System.
Implements camera connectivity monitoring, performance monitoring, and system health indicators.
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from collections import deque, defaultdict

from backend.core.base_service import BaseService
from backend.services.notification_service import NotificationService


class ComponentStatus(Enum):
    """Component health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    ERROR = "error"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class CameraHealth:
    """Camera health status model."""
    camera_id: str
    status: ComponentStatus
    last_frame_time: Optional[datetime]
    frame_rate: float
    connection_uptime: float
    error_count: int
    last_error: Optional[str]
    response_time_ms: float
    timestamp: datetime


@dataclass
class PerformanceMetrics:
    """Performance metrics model."""
    component: str
    avg_processing_time_ms: float
    max_processing_time_ms: float
    min_processing_time_ms: float
    throughput_per_second: float
    error_rate: float
    memory_usage_mb: float
    cpu_usage_percent: float
    timestamp: datetime


@dataclass
class SystemAlert:
    """System alert model."""
    alert_id: str
    component: str
    severity: AlertSeverity
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class SystemHealthReport:
    """Comprehensive system health report."""
    overall_status: ComponentStatus
    camera_health: Dict[str, CameraHealth]
    performance_metrics: Dict[str, PerformanceMetrics]
    active_alerts: List[SystemAlert]
    system_uptime: float
    memory_usage: Dict[str, float]
    cpu_usage: float
    disk_usage: float
    timestamp: datetime


class MonitoringService(BaseService):
    """
    Real-time system monitoring service.
    Monitors camera connectivity, performance metrics, and system health.
    """
    
    def __init__(self, config=None):
        super().__init__(config)
        self.notification_service = NotificationService(config)
        
        # Camera monitoring
        self.camera_health_data: Dict[str, CameraHealth] = {}
        self.camera_monitoring_threads: Dict[str, threading.Thread] = {}
        self.camera_monitoring_active = False
        
        # Performance monitoring
        self.performance_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.processing_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # System monitoring
        self.system_start_time = time.time()
        self.active_alerts: List[SystemAlert] = []
        self.alert_counter = 0
        
        # Monitoring thresholds
        self.thresholds = {
            'max_processing_time_ms': 5000,  # 5 seconds max processing time
            'min_frame_rate': 15,  # Minimum 15 FPS
            'max_error_rate': 0.15,  # Maximum 15% error rate
            'max_memory_usage_mb': 2048,  # Maximum 2GB memory usage
            'max_cpu_usage_percent': 80,  # Maximum 80% CPU usage
            'camera_timeout_seconds': 30,  # Camera timeout threshold
        }
        
        # Start system monitoring thread
        self.system_monitoring_thread = threading.Thread(target=self._system_monitoring_loop, daemon=True)
        self.system_monitoring_active = True
        self.system_monitoring_thread.start()
    
    def register_camera(self, camera_id: str, camera_type: str = "unknown") -> bool:
        """
        Register a camera for monitoring.
        
        Args:
            camera_id: Unique camera identifier
            camera_type: Type of camera (gate, classroom)
            
        Returns:
            bool: True if camera was registered successfully
        """
        try:
            if camera_id in self.camera_health_data:
                self.logger.warning(f"Camera {camera_id} already registered")
                return True
            
            self.camera_health_data[camera_id] = CameraHealth(
                camera_id=camera_id,
                status=ComponentStatus.OFFLINE,
                last_frame_time=None,
                frame_rate=0.0,
                connection_uptime=0.0,
                error_count=0,
                last_error=None,
                response_time_ms=0.0,
                timestamp=datetime.now()
            )
            
            # Start monitoring thread for this camera
            monitor_thread = threading.Thread(
                target=self._monitor_camera,
                args=(camera_id,),
                daemon=True
            )
            self.camera_monitoring_threads[camera_id] = monitor_thread
            monitor_thread.start()
            
            self.logger.info(f"Camera {camera_id} registered for monitoring")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register camera {camera_id}: {str(e)}")
            return False
    
    def unregister_camera(self, camera_id: str) -> bool:
        """
        Unregister a camera from monitoring.
        
        Args:
            camera_id: Camera identifier to unregister
            
        Returns:
            bool: True if camera was unregistered successfully
        """
        try:
            if camera_id not in self.camera_health_data:
                self.logger.warning(f"Camera {camera_id} not registered")
                return True
            
            # Remove from monitoring
            del self.camera_health_data[camera_id]
            
            # Stop monitoring thread (thread will exit when camera not found)
            if camera_id in self.camera_monitoring_threads:
                del self.camera_monitoring_threads[camera_id]
            
            self.logger.info(f"Camera {camera_id} unregistered from monitoring")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to unregister camera {camera_id}: {str(e)}")
            return False
    
    def update_camera_status(self, camera_id: str, frame_received: bool = True, 
                           processing_time_ms: float = 0.0, error: str = None) -> None:
        """
        Update camera status based on recent activity.
        
        Args:
            camera_id: Camera identifier
            frame_received: Whether a frame was successfully received
            processing_time_ms: Time taken to process the frame
            error: Error message if any
        """
        try:
            if camera_id not in self.camera_health_data:
                self.logger.warning(f"Camera {camera_id} not registered for monitoring")
                return
            
            camera_health = self.camera_health_data[camera_id]
            current_time = datetime.now()
            
            if frame_received:
                # Update successful frame reception
                camera_health.last_frame_time = current_time
                camera_health.response_time_ms = processing_time_ms
                
                # Calculate frame rate (simplified)
                if camera_health.status != ComponentStatus.OFFLINE:
                    time_diff = (current_time - camera_health.timestamp).total_seconds()
                    if time_diff > 0:
                        camera_health.frame_rate = 1.0 / time_diff
                
                # Update status based on performance
                if processing_time_ms > self.thresholds['max_processing_time_ms']:
                    camera_health.status = ComponentStatus.DEGRADED
                    self._create_alert(
                        camera_id, AlertSeverity.WARNING,
                        f"Camera {camera_id} processing time exceeded threshold: {processing_time_ms}ms"
                    )
                elif camera_health.frame_rate < self.thresholds['min_frame_rate']:
                    camera_health.status = ComponentStatus.DEGRADED
                    self._create_alert(
                        camera_id, AlertSeverity.WARNING,
                        f"Camera {camera_id} frame rate below threshold: {camera_health.frame_rate} FPS"
                    )
                else:
                    camera_health.status = ComponentStatus.HEALTHY
            
            if error:
                camera_health.error_count += 1
                camera_health.last_error = error
                camera_health.status = ComponentStatus.ERROR
                
                self._create_alert(
                    camera_id, AlertSeverity.ERROR,
                    f"Camera {camera_id} error: {error}"
                )
            
            camera_health.timestamp = current_time
            
        except Exception as e:
            self.logger.error(f"Failed to update camera status for {camera_id}: {str(e)}")
    
    def record_performance_metric(self, component: str, processing_time_ms: float, 
                                success: bool = True, memory_usage_mb: float = 0.0) -> None:
        """
        Record performance metrics for a component.
        
        Args:
            component: Component name (e.g., 'face_recognition', 'emotion_analysis')
            processing_time_ms: Processing time in milliseconds
            success: Whether the operation was successful
            memory_usage_mb: Memory usage in MB
        """
        try:
            # Record processing time
            self.processing_times[component].append({
                'time_ms': processing_time_ms,
                'success': success,
                'timestamp': time.time(),
                'memory_mb': memory_usage_mb
            })
            
            # Calculate metrics
            recent_times = [
                entry['time_ms'] for entry in list(self.processing_times[component])[-50:]
            ]
            recent_successes = [
                entry['success'] for entry in list(self.processing_times[component])[-50:]
            ]
            
            if recent_times:
                avg_time = sum(recent_times) / len(recent_times)
                max_time = max(recent_times)
                min_time = min(recent_times)
                error_rate = 1.0 - (sum(recent_successes) / len(recent_successes))
                throughput = len(recent_times) / 60.0  # Operations per second (last minute)
                
                # Check thresholds and create alerts
                if avg_time > self.thresholds['max_processing_time_ms']:
                    self._create_alert(
                        component, AlertSeverity.WARNING,
                        f"{component} average processing time exceeded threshold: {avg_time:.2f}ms"
                    )
                
                if error_rate > self.thresholds['max_error_rate']:
                    self._create_alert(
                        component, AlertSeverity.ERROR,
                        f"{component} error rate exceeded threshold: {error_rate:.2%}"
                    )
                
                # Store aggregated metrics
                self.performance_data[component].append(PerformanceMetrics(
                    component=component,
                    avg_processing_time_ms=avg_time,
                    max_processing_time_ms=max_time,
                    min_processing_time_ms=min_time,
                    throughput_per_second=throughput,
                    error_rate=error_rate,
                    memory_usage_mb=memory_usage_mb,
                    cpu_usage_percent=psutil.cpu_percent(),
                    timestamp=datetime.now()
                ))
            
        except Exception as e:
            self.logger.error(f"Failed to record performance metric for {component}: {str(e)}")
    
    def get_camera_health(self, camera_id: str = None) -> Dict[str, CameraHealth]:
        """
        Get camera health status.
        
        Args:
            camera_id: Specific camera ID, or None for all cameras
            
        Returns:
            Dict of camera health data
        """
        try:
            if camera_id:
                if camera_id in self.camera_health_data:
                    return {camera_id: self.camera_health_data[camera_id]}
                else:
                    return {}
            else:
                return self.camera_health_data.copy()
                
        except Exception as e:
            self.logger.error(f"Failed to get camera health: {str(e)}")
            return {}
    
    def get_performance_metrics(self, component: str = None) -> Dict[str, PerformanceMetrics]:
        """
        Get performance metrics.
        
        Args:
            component: Specific component name, or None for all components
            
        Returns:
            Dict of performance metrics
        """
        try:
            result = {}
            
            if component:
                if component in self.performance_data and self.performance_data[component]:
                    result[component] = list(self.performance_data[component])[-1]
            else:
                for comp_name, metrics_deque in self.performance_data.items():
                    if metrics_deque:
                        result[comp_name] = list(metrics_deque)[-1]
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {str(e)}")
            return {}
    
    def get_system_health_report(self) -> SystemHealthReport:
        """
        Get comprehensive system health report.
        
        Returns:
            SystemHealthReport with all system status information
        """
        try:
            # Calculate overall system status
            overall_status = self._calculate_overall_status()
            
            # Get system resource usage
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')
            
            memory_usage = {
                'total_mb': memory_info.total / (1024 * 1024),
                'used_mb': memory_info.used / (1024 * 1024),
                'available_mb': memory_info.available / (1024 * 1024),
                'percent': memory_info.percent
            }
            
            # Get latest performance metrics
            latest_metrics = {}
            for component, metrics_deque in self.performance_data.items():
                if metrics_deque:
                    latest_metrics[component] = list(metrics_deque)[-1]
            
            return SystemHealthReport(
                overall_status=overall_status,
                camera_health=self.camera_health_data.copy(),
                performance_metrics=latest_metrics,
                active_alerts=self.active_alerts.copy(),
                system_uptime=time.time() - self.system_start_time,
                memory_usage=memory_usage,
                cpu_usage=psutil.cpu_percent(),
                disk_usage=disk_info.percent,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate system health report: {str(e)}")
            return SystemHealthReport(
                overall_status=ComponentStatus.ERROR,
                camera_health={},
                performance_metrics={},
                active_alerts=[],
                system_uptime=0,
                memory_usage={},
                cpu_usage=0,
                disk_usage=0,
                timestamp=datetime.now()
            )
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an active alert.
        
        Args:
            alert_id: Alert identifier
            
        Returns:
            bool: True if alert was acknowledged
        """
        try:
            for alert in self.active_alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    self.logger.info(f"Alert {alert_id} acknowledged")
                    return True
            
            self.logger.warning(f"Alert {alert_id} not found")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to acknowledge alert {alert_id}: {str(e)}")
            return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """
        Resolve an active alert.
        
        Args:
            alert_id: Alert identifier
            
        Returns:
            bool: True if alert was resolved
        """
        try:
            for i, alert in enumerate(self.active_alerts):
                if alert.alert_id == alert_id:
                    alert.resolved = True
                    resolved_alert = self.active_alerts.pop(i)
                    self.logger.info(f"Alert {alert_id} resolved")
                    return True
            
            self.logger.warning(f"Alert {alert_id} not found")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to resolve alert {alert_id}: {str(e)}")
            return False
    
    def _monitor_camera(self, camera_id: str) -> None:
        """
        Monitor a specific camera in a separate thread.
        
        Args:
            camera_id: Camera identifier to monitor
        """
        self.logger.info(f"Starting camera monitoring for {camera_id}")
        
        while camera_id in self.camera_health_data and self.camera_monitoring_active:
            try:
                camera_health = self.camera_health_data[camera_id]
                current_time = datetime.now()
                
                # Check if camera has been inactive
                if camera_health.last_frame_time:
                    time_since_last_frame = (current_time - camera_health.last_frame_time).total_seconds()
                    
                    if time_since_last_frame > self.thresholds['camera_timeout_seconds']:
                        if camera_health.status != ComponentStatus.OFFLINE:
                            camera_health.status = ComponentStatus.OFFLINE
                            self._create_alert(
                                camera_id, AlertSeverity.CRITICAL,
                                f"Camera {camera_id} offline - no frames received for {time_since_last_frame:.1f} seconds"
                            )
                
                # Update connection uptime
                if camera_health.status in [ComponentStatus.HEALTHY, ComponentStatus.DEGRADED]:
                    camera_health.connection_uptime = (current_time - camera_health.timestamp).total_seconds()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self.logger.error(f"Error monitoring camera {camera_id}: {str(e)}")
                time.sleep(10)  # Wait longer on error
        
        self.logger.info(f"Camera monitoring stopped for {camera_id}")
    
    def _system_monitoring_loop(self) -> None:
        """System-wide monitoring loop running in background thread."""
        self.logger.info("Starting system monitoring loop")
        
        while self.system_monitoring_active:
            try:
                # Monitor system resources
                memory_percent = psutil.virtual_memory().percent
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Check resource thresholds
                if memory_percent > 90:
                    self._create_alert(
                        "system", AlertSeverity.CRITICAL,
                        f"High memory usage: {memory_percent:.1f}%"
                    )
                elif memory_percent > 80:
                    self._create_alert(
                        "system", AlertSeverity.WARNING,
                        f"Elevated memory usage: {memory_percent:.1f}%"
                    )
                
                if cpu_percent > self.thresholds['max_cpu_usage_percent']:
                    self._create_alert(
                        "system", AlertSeverity.WARNING,
                        f"High CPU usage: {cpu_percent:.1f}%"
                    )
                
                # Clean up old resolved alerts
                self._cleanup_old_alerts()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in system monitoring loop: {str(e)}")
                time.sleep(60)  # Wait longer on error
        
        self.logger.info("System monitoring loop stopped")
    
    def _create_alert(self, component: str, severity: AlertSeverity, message: str) -> None:
        """
        Create a new system alert.
        
        Args:
            component: Component that triggered the alert
            severity: Alert severity level
            message: Alert message
        """
        try:
            # Check if similar alert already exists
            for alert in self.active_alerts:
                if (alert.component == component and 
                    alert.severity == severity and 
                    alert.message == message and 
                    not alert.resolved):
                    return  # Don't create duplicate alerts
            
            self.alert_counter += 1
            alert = SystemAlert(
                alert_id=f"alert_{self.alert_counter}_{int(time.time())}",
                component=component,
                severity=severity,
                message=message,
                details={"timestamp": datetime.now().isoformat()},
                timestamp=datetime.now()
            )
            
            self.active_alerts.append(alert)
            
            # Send notification for critical and error alerts
            if severity in [AlertSeverity.CRITICAL, AlertSeverity.ERROR]:
                recipients = ["admin", "tech_support"]
                if component.startswith("camera"):
                    recipients.append("faculty")
                
                self.notification_service.send_alert(message, recipients)
            
            self.logger.log(
                logging.CRITICAL if severity == AlertSeverity.CRITICAL else
                logging.ERROR if severity == AlertSeverity.ERROR else
                logging.WARNING,
                f"ALERT [{severity.value.upper()}] {component}: {message}"
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create alert: {str(e)}")
    
    def _calculate_overall_status(self) -> ComponentStatus:
        """Calculate overall system status based on component health."""
        try:
            if not self.camera_health_data and not self.performance_data:
                return ComponentStatus.OFFLINE
            
            # Check for critical alerts
            critical_alerts = [a for a in self.active_alerts 
                             if a.severity == AlertSeverity.CRITICAL and not a.resolved]
            if critical_alerts:
                return ComponentStatus.UNHEALTHY
            
            # Check camera health
            camera_statuses = [health.status for health in self.camera_health_data.values()]
            if camera_statuses:
                if any(status == ComponentStatus.ERROR for status in camera_statuses):
                    return ComponentStatus.UNHEALTHY
                elif any(status == ComponentStatus.OFFLINE for status in camera_statuses):
                    return ComponentStatus.DEGRADED
                elif any(status == ComponentStatus.DEGRADED for status in camera_statuses):
                    return ComponentStatus.DEGRADED
            
            # Check for error alerts
            error_alerts = [a for a in self.active_alerts 
                          if a.severity == AlertSeverity.ERROR and not a.resolved]
            if error_alerts:
                return ComponentStatus.DEGRADED
            
            return ComponentStatus.HEALTHY
            
        except Exception as e:
            self.logger.error(f"Failed to calculate overall status: {str(e)}")
            return ComponentStatus.ERROR
    
    def _cleanup_old_alerts(self) -> None:
        """Clean up old resolved alerts."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            # Remove resolved alerts older than 24 hours
            self.active_alerts = [
                alert for alert in self.active_alerts
                if not (alert.resolved and alert.timestamp < cutoff_time)
            ]
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old alerts: {str(e)}")
    
    def shutdown(self) -> None:
        """Shutdown monitoring service and cleanup resources."""
        try:
            self.logger.info("Shutting down monitoring service")
            
            # Stop monitoring
            self.camera_monitoring_active = False
            self.system_monitoring_active = False
            
            # Wait for threads to finish
            for thread in self.camera_monitoring_threads.values():
                if thread.is_alive():
                    thread.join(timeout=5)
            
            if self.system_monitoring_thread.is_alive():
                self.system_monitoring_thread.join(timeout=5)
            
            self.logger.info("Monitoring service shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during monitoring service shutdown: {str(e)}")
        
        # Camera monitoring
        self.camera_health_data: Dict[str, CameraHealth] = {}
        self.camera_monitoring_threads: Dict[str, threading.Thread] = {}
        self.camera_monitoring_active = False
        
        # Performance monitoring
        self.performance_data: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.processing_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # System monitoring
        self.system_start_time = time.time()
        self.active_alerts: List[SystemAlert] = []
        self.alert_counter = 0
        
        # 
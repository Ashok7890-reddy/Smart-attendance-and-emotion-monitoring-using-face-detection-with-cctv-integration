"""
Prometheus metrics collection for Smart Attendance System
"""
import time
import functools
from typing import Dict, Any, Optional, Callable
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
import os
import logging
from contextlib import contextmanager

# Initialize logger
logger = logging.getLogger('smart_attendance.metrics')

# Service-wide metrics
SERVICE_INFO = Info('smart_attendance_service_info', 'Service information')
SERVICE_UPTIME = Gauge('smart_attendance_uptime_seconds', 'Service uptime in seconds')
SERVICE_HEALTH = Gauge('smart_attendance_service_health', 'Service health status (1=healthy, 0=unhealthy)')

# Face Recognition Metrics
FACE_RECOGNITION_REQUESTS = Counter(
    'face_recognition_requests_total',
    'Total number of face recognition requests',
    ['service', 'camera_location', 'status']
)

FACE_RECOGNITION_DURATION = Histogram(
    'face_recognition_processing_duration_seconds',
    'Time spent processing face recognition requests',
    ['service', 'operation'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

FACE_RECOGNITION_ACCURACY = Gauge(
    'face_recognition_accuracy_percentage',
    'Face recognition accuracy percentage',
    ['service']
)

LIVENESS_DETECTION_REQUESTS = Counter(
    'liveness_detection_requests_total',
    'Total number of liveness detection requests',
    ['service', 'result']
)

FACE_EMBEDDINGS_STORED = Counter(
    'face_embeddings_stored_total',
    'Total number of face embeddings stored',
    ['service']
)

# Emotion Analysis Metrics
EMOTION_ANALYSIS_REQUESTS = Counter(
    'emotion_analysis_requests_total',
    'Total number of emotion analysis requests',
    ['service', 'emotion_type']
)

EMOTION_ANALYSIS_DURATION = Histogram(
    'emotion_analysis_processing_duration_seconds',
    'Time spent processing emotion analysis requests',
    ['service'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)

EMOTION_DISTRIBUTION = Counter(
    'emotion_detected_total',
    'Distribution of detected emotions',
    ['service', 'emotion', 'session_id']
)

ENGAGEMENT_SCORE = Gauge(
    'engagement_score_current',
    'Current engagement score for active sessions',
    ['service', 'session_id', 'class_id']
)

# Attendance Management Metrics
ATTENDANCE_SESSIONS = Gauge(
    'attendance_sessions_active_total',
    'Number of active attendance sessions',
    ['service']
)

STUDENTS_DETECTED = Counter(
    'students_detected_total',
    'Total number of students detected',
    ['service', 'student_type', 'camera_location']
)

ATTENDANCE_VALIDATION_FAILURES = Counter(
    'attendance_validation_failures_total',
    'Total number of attendance validation failures',
    ['service', 'failure_type']
)

CROSS_VERIFICATION_REQUESTS = Counter(
    'cross_verification_requests_total',
    'Total number of cross-verification requests for day scholars',
    ['service', 'status']
)

# System Performance Metrics
CAMERA_CONNECTIVITY = Gauge(
    'camera_connectivity_status',
    'Camera connectivity status (1=connected, 0=disconnected)',
    ['camera_location', 'camera_id']
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Number of active database connections',
    ['service', 'database_type']
)

REDIS_CACHE_HITS = Counter(
    'redis_cache_hits_total',
    'Total number of Redis cache hits',
    ['service', 'cache_type']
)

REDIS_CACHE_MISSES = Counter(
    'redis_cache_misses_total',
    'Total number of Redis cache misses',
    ['service', 'cache_type']
)

# API Metrics
HTTP_REQUESTS = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['service', 'method', 'endpoint', 'status_code']
)

HTTP_REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['service', 'method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)

WEBSOCKET_CONNECTIONS = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections',
    ['service']
)

# Error Metrics
ERROR_RATE = Counter(
    'errors_total',
    'Total number of errors',
    ['service', 'error_type', 'severity']
)


class MetricsCollector:
    """Central metrics collector for the Smart Attendance System"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.start_time = time.time()
        
        # Set service info
        SERVICE_INFO.info({
            'service': service_name,
            'version': os.getenv('SERVICE_VERSION', '1.0.0'),
            'environment': os.getenv('ENVIRONMENT', 'development')
        })
        
        logger.info(f"Metrics collector initialized for service: {service_name}")
    
    def update_uptime(self):
        """Update service uptime metric"""
        uptime = time.time() - self.start_time
        SERVICE_UPTIME.set(uptime)
    
    def set_health_status(self, is_healthy: bool):
        """Set service health status"""
        SERVICE_HEALTH.set(1 if is_healthy else 0)
    
    def record_face_recognition_request(self, camera_location: str, status: str, duration: float = None):
        """Record face recognition request metrics"""
        FACE_RECOGNITION_REQUESTS.labels(
            service=self.service_name,
            camera_location=camera_location,
            status=status
        ).inc()
        
        if duration is not None:
            FACE_RECOGNITION_DURATION.labels(
                service=self.service_name,
                operation='recognition'
            ).observe(duration)
    
    def update_face_recognition_accuracy(self, accuracy: float):
        """Update face recognition accuracy metric"""
        FACE_RECOGNITION_ACCURACY.labels(service=self.service_name).set(accuracy)
    
    def record_liveness_detection(self, result: str):
        """Record liveness detection request"""
        LIVENESS_DETECTION_REQUESTS.labels(
            service=self.service_name,
            result=result
        ).inc()
    
    def record_emotion_analysis(self, emotion_type: str, duration: float = None):
        """Record emotion analysis metrics"""
        EMOTION_ANALYSIS_REQUESTS.labels(
            service=self.service_name,
            emotion_type=emotion_type
        ).inc()
        
        if duration is not None:
            EMOTION_ANALYSIS_DURATION.labels(service=self.service_name).observe(duration)
    
    def record_emotion_detection(self, emotion: str, session_id: str):
        """Record detected emotion"""
        EMOTION_DISTRIBUTION.labels(
            service=self.service_name,
            emotion=emotion,
            session_id=session_id
        ).inc()
    
    def update_engagement_score(self, session_id: str, class_id: str, score: float):
        """Update engagement score for a session"""
        ENGAGEMENT_SCORE.labels(
            service=self.service_name,
            session_id=session_id,
            class_id=class_id
        ).set(score)
    
    def update_active_sessions(self, count: int):
        """Update active attendance sessions count"""
        ATTENDANCE_SESSIONS.labels(service=self.service_name).set(count)
    
    def record_student_detection(self, student_type: str, camera_location: str):
        """Record student detection"""
        STUDENTS_DETECTED.labels(
            service=self.service_name,
            student_type=student_type,
            camera_location=camera_location
        ).inc()
    
    def record_validation_failure(self, failure_type: str):
        """Record attendance validation failure"""
        ATTENDANCE_VALIDATION_FAILURES.labels(
            service=self.service_name,
            failure_type=failure_type
        ).inc()
    
    def record_cross_verification(self, status: str):
        """Record cross-verification request"""
        CROSS_VERIFICATION_REQUESTS.labels(
            service=self.service_name,
            status=status
        ).inc()
    
    def update_camera_connectivity(self, camera_location: str, camera_id: str, is_connected: bool):
        """Update camera connectivity status"""
        CAMERA_CONNECTIVITY.labels(
            camera_location=camera_location,
            camera_id=camera_id
        ).set(1 if is_connected else 0)
    
    def update_database_connections(self, database_type: str, count: int):
        """Update database connections count"""
        DATABASE_CONNECTIONS.labels(
            service=self.service_name,
            database_type=database_type
        ).set(count)
    
    def record_cache_hit(self, cache_type: str):
        """Record cache hit"""
        REDIS_CACHE_HITS.labels(
            service=self.service_name,
            cache_type=cache_type
        ).inc()
    
    def record_cache_miss(self, cache_type: str):
        """Record cache miss"""
        REDIS_CACHE_MISSES.labels(
            service=self.service_name,
            cache_type=cache_type
        ).inc()
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        HTTP_REQUESTS.labels(
            service=self.service_name,
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        HTTP_REQUEST_DURATION.labels(
            service=self.service_name,
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def update_websocket_connections(self, count: int):
        """Update active WebSocket connections count"""
        WEBSOCKET_CONNECTIONS.labels(service=self.service_name).set(count)
    
    def record_error(self, error_type: str, severity: str = 'error'):
        """Record error occurrence"""
        ERROR_RATE.labels(
            service=self.service_name,
            error_type=error_type,
            severity=severity
        ).inc()


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def initialize_metrics(service_name: str, port: int = 8000) -> MetricsCollector:
    """
    Initialize metrics collection for a service
    
    Args:
        service_name: Name of the service
        port: Port to expose metrics on (default: 8000)
        
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    
    _metrics_collector = MetricsCollector(service_name)
    
    # Start Prometheus metrics server
    try:
        start_http_server(port, addr='0.0.0.0')
        logger.info(f"Metrics server started on port {port}")
    except Exception as e:
        logger.error(f"Failed to start metrics server: {e}")
    
    return _metrics_collector


def get_metrics_collector() -> Optional[MetricsCollector]:
    """Get the global metrics collector instance"""
    return _metrics_collector


@contextmanager
def measure_time(metric_name: str, labels: Dict[str, str] = None):
    """
    Context manager to measure execution time
    
    Args:
        metric_name: Name of the metric to record
        labels: Additional labels for the metric
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        if _metrics_collector:
            # Record the duration based on metric type
            if 'face_recognition' in metric_name:
                _metrics_collector.record_face_recognition_request(
                    camera_location=labels.get('camera_location', 'unknown'),
                    status='success',
                    duration=duration
                )
            elif 'emotion_analysis' in metric_name:
                _metrics_collector.record_emotion_analysis(
                    emotion_type=labels.get('emotion_type', 'unknown'),
                    duration=duration
                )


def metrics_decorator(metric_name: str, **labels):
    """
    Decorator to automatically measure function execution time
    
    Args:
        metric_name: Name of the metric to record
        **labels: Additional labels for the metric
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with measure_time(metric_name, labels):
                return func(*args, **kwargs)
        return wrapper
    return decorator
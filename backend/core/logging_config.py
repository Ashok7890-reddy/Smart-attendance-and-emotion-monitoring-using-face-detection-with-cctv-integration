"""
Centralized logging configuration for Smart Attendance System
"""
import logging
import logging.config
import os
import sys
from datetime import datetime
from typing import Dict, Any
import json
from fluent import sender
from fluent.handler import FluentHandler


class SecurityAuditFilter(logging.Filter):
    """Filter for security and audit-related log messages"""
    
    def filter(self, record):
        security_keywords = [
            'authentication', 'authorization', 'biometric', 
            'face_embedding', 'security', 'access_denied',
            'login_attempt', 'encryption', 'decryption'
        ]
        return any(keyword in record.getMessage().lower() for keyword in security_keywords)


class PerformanceFilter(logging.Filter):
    """Filter for performance-related log messages"""
    
    def filter(self, record):
        performance_keywords = [
            'processing_time', 'latency', 'performance', 
            'response_time', 'duration', 'benchmark'
        ]
        return any(keyword in record.getMessage().lower() for keyword in performance_keywords)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'service': os.getenv('SERVICE_NAME', 'unknown'),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'thread_id': record.thread,
            'process_id': record.process
        }
        
        # Add exception information if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
            
        return json.dumps(log_entry)


def setup_logging(service_name: str = None, log_level: str = None) -> None:
    """
    Setup centralized logging configuration
    
    Args:
        service_name: Name of the service (face_recognition, emotion_analysis, etc.)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    # Get configuration from environment
    service_name = service_name or os.getenv('SERVICE_NAME', 'smart_attendance')
    log_level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    environment = os.getenv('ENVIRONMENT', 'development')
    fluentd_host = os.getenv('FLUENTD_HOST', 'fluentd')
    fluentd_port = int(os.getenv('FLUENTD_PORT', '24224'))
    
    # Create logs directory if it doesn't exist
    log_dir = '/app/logs'
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure Fluentd sender
    fluent_sender = sender.FluentSender(
        tag=f'smart_attendance.{service_name}',
        host=fluentd_host,
        port=fluentd_port
    )
    
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'structured': {
                '()': StructuredFormatter
            },
            'detailed': {
                'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(funcName)s(): %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'filters': {
            'security_audit': {
                '()': SecurityAuditFilter
            },
            'performance': {
                '()': PerformanceFilter
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'standard',
                'stream': sys.stdout
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'detailed',
                'filename': f'{log_dir}/{service_name}.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            },
            'structured_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': log_level,
                'formatter': 'structured',
                'filename': f'{log_dir}/{service_name}_structured.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            },
            'security_audit': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'structured',
                'filename': f'{log_dir}/{service_name}_security.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10,
                'filters': ['security_audit']
            },
            'performance': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'structured',
                'filename': f'{log_dir}/{service_name}_performance.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'filters': ['performance']
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filename': f'{log_dir}/{service_name}_errors.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10
            }
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console', 'file', 'structured_file'],
                'level': log_level,
                'propagate': False
            },
            'smart_attendance': {
                'handlers': ['console', 'file', 'structured_file', 'security_audit', 'performance', 'error_file'],
                'level': log_level,
                'propagate': False
            },
            'security': {
                'handlers': ['security_audit', 'error_file'],
                'level': 'INFO',
                'propagate': False
            },
            'performance': {
                'handlers': ['performance'],
                'level': 'INFO',
                'propagate': False
            }
        }
    }
    
    # Add Fluentd handler in production
    if environment == 'production' and fluent_sender:
        logging_config['handlers']['fluentd'] = {
            'class': 'fluent.handler.FluentHandler',
            'level': log_level,
            'formatter': 'structured',
            'tag': f'smart_attendance.{service_name}',
            'host': fluentd_host,
            'port': fluentd_port
        }
        
        # Add fluentd handler to loggers
        for logger_name in logging_config['loggers']:
            if 'handlers' in logging_config['loggers'][logger_name]:
                logging_config['loggers'][logger_name]['handlers'].append('fluentd')
    
    logging.config.dictConfig(logging_config)
    
    # Log startup message
    logger = logging.getLogger('smart_attendance.startup')
    logger.info(f"Logging configured for service: {service_name}, level: {log_level}, environment: {environment}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f'smart_attendance.{name}')


def log_security_event(event_type: str, details: Dict[str, Any], user_id: str = None) -> None:
    """
    Log security-related events for audit purposes
    
    Args:
        event_type: Type of security event (authentication, authorization, etc.)
        details: Event details
        user_id: User ID if applicable
    """
    logger = logging.getLogger('security')
    
    security_log = {
        'event_type': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'details': details,
        'service': os.getenv('SERVICE_NAME', 'unknown')
    }
    
    logger.info(f"Security event: {event_type}", extra={'extra_fields': security_log})


def log_performance_metric(metric_name: str, value: float, unit: str = 'seconds', **kwargs) -> None:
    """
    Log performance metrics
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        unit: Unit of measurement
        **kwargs: Additional metric attributes
    """
    logger = logging.getLogger('performance')
    
    performance_log = {
        'metric_name': metric_name,
        'value': value,
        'unit': unit,
        'timestamp': datetime.utcnow().isoformat(),
        'service': os.getenv('SERVICE_NAME', 'unknown'),
        **kwargs
    }
    
    logger.info(f"Performance metric: {metric_name}={value}{unit}", extra={'extra_fields': performance_log})


class LoggingContextManager:
    """Context manager for adding request/session context to logs"""
    
    def __init__(self, **context):
        self.context = context
        self.old_factory = logging.getLogRecordFactory()
    
    def __enter__(self):
        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record
        
        logging.setLogRecordFactory(record_factory)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self.old_factory)
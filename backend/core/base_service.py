"""
Base service classes for the Smart Attendance System.
"""

from abc import ABC
import logging
from typing import Optional
from backend.core.config import Config


class BaseService(ABC):
    """Base class for all services."""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.config.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def health_check(self) -> dict:
        """Basic health check for the service."""
        return {
            "service": self.__class__.__name__,
            "status": "healthy",
            "timestamp": self.config.get_current_timestamp()
        }


class BaseCameraService(BaseService):
    """Base class for camera-related services."""
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.camera_connections = {}
    
    def _validate_camera_id(self, camera_id: str) -> bool:
        """Validate camera ID format."""
        return camera_id and isinstance(camera_id, str) and len(camera_id) > 0
    
    def _log_camera_event(self, camera_id: str, event: str, success: bool = True):
        """Log camera events."""
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, f"Camera {camera_id}: {event}")


class BaseProcessingService(BaseService):
    """Base class for processing services."""
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.processing_stats = {
            "total_processed": 0,
            "successful_processed": 0,
            "failed_processed": 0
        }
    
    def _update_stats(self, success: bool = True):
        """Update processing statistics."""
        self.processing_stats["total_processed"] += 1
        if success:
            self.processing_stats["successful_processed"] += 1
        else:
            self.processing_stats["failed_processed"] += 1
    
    def get_processing_stats(self) -> dict:
        """Get current processing statistics."""
        return self.processing_stats.copy()


class BaseRepository(BaseService):
    """Base repository class."""
    
    def __init__(self, config: Optional[Config] = None):
        super().__init__(config)
        self.connection = None
    
    def _validate_entity_id(self, entity_id: str) -> bool:
        """Validate entity ID format."""
        return entity_id and isinstance(entity_id, str) and len(entity_id) > 0
    
    def _log_operation(self, operation: str, entity_id: str, success: bool = True):
        """Log repository operations."""
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, f"{operation} operation for {entity_id}: {'Success' if success else 'Failed'}")
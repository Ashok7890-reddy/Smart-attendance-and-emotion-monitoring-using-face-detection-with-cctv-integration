"""
Configuration management for the Smart Attendance System.
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """Database configuration."""
    host: str = "localhost"
    port: int = 5432
    database: str = "smart_attendance"
    username: str = "postgres"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class RedisConfig:
    """Redis configuration."""
    host: str = "localhost"
    port: int = 6379
    database: int = 0
    password: Optional[str] = None
    max_connections: int = 10


@dataclass
class CameraConfig:
    """Camera configuration."""
    gate_camera_id: str = "gate_cam_01"
    classroom_camera_ids: list = field(default_factory=lambda: ["class_cam_01"])
    frame_rate: int = 30
    resolution_width: int = 1920
    resolution_height: int = 1080
    reconnect_attempts: int = 3
    reconnect_delay: int = 5


@dataclass
class FaceRecognitionConfig:
    """Face recognition configuration."""
    model_path: str = "models/facenet.pb"
    confidence_threshold: float = 0.85
    liveness_threshold: float = 0.7
    max_processing_time: int = 2
    embedding_dimension: int = 512


@dataclass
class EmotionAnalysisConfig:
    """Emotion analysis configuration."""
    model_path: str = "models/emotion_classifier.h5"
    confidence_threshold: float = 0.6
    engagement_weights: Dict[str, float] = field(default_factory=lambda: {
        "interested": 1.0,
        "bored": -0.5,
        "confused": 0.0
    })
    update_interval: int = 5


@dataclass
class SecurityConfig:
    """Security configuration."""
    encryption_key: str = ""
    jwt_secret: str = ""
    jwt_expiration: int = 3600
    api_rate_limit: int = 100
    enable_audit_logging: bool = True


class Config:
    """Main configuration class."""
    
    def __init__(self):
        self.ENV = os.getenv("ENVIRONMENT", "development")
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # Service configurations
        self.database = self._load_database_config()
        self.redis = self._load_redis_config()
        self.camera = self._load_camera_config()
        self.face_recognition = self._load_face_recognition_config()
        self.emotion_analysis = self._load_emotion_analysis_config()
        self.security = self._load_security_config()
        
        # API configuration
        self.API_HOST = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT = int(os.getenv("API_PORT", "8000"))
        self.API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
        
        # WebSocket configuration
        self.WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "0.0.0.0")
        self.WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "8001"))
        
        # File paths
        self.MODELS_DIR = os.getenv("MODELS_DIR", "models")
        self.LOGS_DIR = os.getenv("LOGS_DIR", "logs")
        self.DATA_DIR = os.getenv("DATA_DIR", "data")
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration from environment."""
        return DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "smart_attendance"),
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20"))
        )
    
    def _load_redis_config(self) -> RedisConfig:
        """Load Redis configuration from environment."""
        return RedisConfig(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            database=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD"),
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
        )
    
    def _load_camera_config(self) -> CameraConfig:
        """Load camera configuration from environment."""
        classroom_cameras = os.getenv("CLASSROOM_CAMERA_IDS", "class_cam_01").split(",")
        return CameraConfig(
            gate_camera_id=os.getenv("GATE_CAMERA_ID", "gate_cam_01"),
            classroom_camera_ids=classroom_cameras,
            frame_rate=int(os.getenv("CAMERA_FRAME_RATE", "30")),
            resolution_width=int(os.getenv("CAMERA_WIDTH", "1920")),
            resolution_height=int(os.getenv("CAMERA_HEIGHT", "1080")),
            reconnect_attempts=int(os.getenv("CAMERA_RECONNECT_ATTEMPTS", "3")),
            reconnect_delay=int(os.getenv("CAMERA_RECONNECT_DELAY", "5"))
        )
    
    def _load_face_recognition_config(self) -> FaceRecognitionConfig:
        """Load face recognition configuration from environment."""
        return FaceRecognitionConfig(
            model_path=os.getenv("FACE_MODEL_PATH", "models/facenet.pb"),
            confidence_threshold=float(os.getenv("FACE_CONFIDENCE_THRESHOLD", "0.85")),
            liveness_threshold=float(os.getenv("LIVENESS_THRESHOLD", "0.7")),
            max_processing_time=int(os.getenv("FACE_MAX_PROCESSING_TIME", "2")),
            embedding_dimension=int(os.getenv("FACE_EMBEDDING_DIM", "512"))
        )
    
    def _load_emotion_analysis_config(self) -> EmotionAnalysisConfig:
        """Load emotion analysis configuration from environment."""
        return EmotionAnalysisConfig(
            model_path=os.getenv("EMOTION_MODEL_PATH", "models/emotion_classifier.h5"),
            confidence_threshold=float(os.getenv("EMOTION_CONFIDENCE_THRESHOLD", "0.6")),
            update_interval=int(os.getenv("EMOTION_UPDATE_INTERVAL", "5"))
        )
    
    def _load_security_config(self) -> SecurityConfig:
        """Load security configuration from environment."""
        return SecurityConfig(
            encryption_key=os.getenv("ENCRYPTION_KEY", ""),
            jwt_secret=os.getenv("JWT_SECRET", ""),
            jwt_expiration=int(os.getenv("JWT_EXPIRATION", "3600")),
            api_rate_limit=int(os.getenv("API_RATE_LIMIT", "100")),
            enable_audit_logging=os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true"
        )
    
    def get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENV.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENV.lower() == "development"



# Global settings instance
_settings = None


def get_settings() -> Config:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = Config()
    return _settings

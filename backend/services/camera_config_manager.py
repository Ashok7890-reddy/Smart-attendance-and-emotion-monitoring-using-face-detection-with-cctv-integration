"""
Camera Configuration Manager for handling different camera setups and configurations.

This service manages camera configurations, supports different camera types,
and handles edge device specific settings.
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from backend.core.base_service import BaseService
from backend.services.camera_service import CameraConfig
from backend.models.face_detection import CameraLocation


class CameraType(Enum):
    """Types of supported cameras."""
    USB_CAMERA = "usb_camera"
    IP_CAMERA = "ip_camera"
    RTSP_STREAM = "rtsp_stream"
    HTTP_STREAM = "http_stream"
    FILE_SOURCE = "file_source"
    MOCK_CAMERA = "mock_camera"


class EdgeDeviceType(Enum):
    """Types of edge devices."""
    NVIDIA_JETSON_NANO = "nvidia_jetson_nano"
    NVIDIA_JETSON_XAVIER = "nvidia_jetson_xavier"
    NVIDIA_JETSON_ORIN = "nvidia_jetson_orin"
    RASPBERRY_PI = "raspberry_pi"
    INTEL_NUC = "intel_nuc"
    GENERIC_LINUX = "generic_linux"


@dataclass
class EdgeDeviceConfig:
    """Configuration for edge devices."""
    device_id: str
    device_type: EdgeDeviceType
    ip_address: str
    port: int = 8080
    api_key: Optional[str] = None
    max_concurrent_streams: int = 2
    processing_capabilities: Dict[str, bool] = None
    hardware_acceleration: bool = True
    memory_limit_mb: int = 2048
    cpu_limit_percent: int = 80
    
    def __post_init__(self):
        if self.processing_capabilities is None:
            self.processing_capabilities = {
                "face_detection": True,
                "emotion_analysis": True,
                "liveness_detection": True,
                "preprocessing": True
            }


@dataclass
class CameraConfigExtended:
    """Extended camera configuration with additional settings."""
    camera_id: str
    camera_type: CameraType
    location: CameraLocation
    source: str
    resolution: tuple = (1280, 720)
    fps: int = 30
    buffer_size: int = 10
    retry_attempts: int = 3
    retry_delay: float = 5.0
    
    # Advanced settings
    exposure: Optional[int] = None
    brightness: Optional[int] = None
    contrast: Optional[int] = None
    saturation: Optional[int] = None
    auto_focus: bool = True
    zoom: float = 1.0
    
    # Network settings (for IP cameras)
    username: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    
    # Edge processing settings
    edge_device_id: Optional[str] = None
    edge_processing_enabled: bool = False
    
    # Quality settings
    min_face_size: int = 80
    quality_threshold: float = 0.5
    detection_confidence: float = 0.7
    
    # Recording settings
    record_enabled: bool = False
    record_path: Optional[str] = None
    record_duration_hours: int = 24
    
    def to_camera_config(self) -> CameraConfig:
        """Convert to basic CameraConfig for camera service."""
        return CameraConfig(
            camera_id=self.camera_id,
            location=self.location,
            source=self.source,
            resolution=self.resolution,
            fps=self.fps,
            buffer_size=self.buffer_size,
            retry_attempts=self.retry_attempts,
            retry_delay=self.retry_delay
        )


class CameraConfigManager(BaseService):
    """Manager for camera configurations and edge device settings."""
    
    def __init__(self, config=None, config_file_path: str = "camera_configs.json"):
        super().__init__(config)
        self.config_file_path = config_file_path
        self.camera_configs: Dict[str, CameraConfigExtended] = {}
        self.edge_devices: Dict[str, EdgeDeviceConfig] = {}
        
        # Load configurations
        self._load_configurations()
        
        # Setup default configurations if none exist
        if not self.camera_configs:
            self._setup_default_configurations()
    
    def _load_configurations(self):
        """Load configurations from file."""
        try:
            if os.path.exists(self.config_file_path):
                with open(self.config_file_path, 'r') as f:
                    data = json.load(f)
                
                # Load camera configurations
                for camera_data in data.get("cameras", []):
                    camera_config = self._dict_to_camera_config(camera_data)
                    self.camera_configs[camera_config.camera_id] = camera_config
                
                # Load edge device configurations
                for device_data in data.get("edge_devices", []):
                    device_config = self._dict_to_edge_device_config(device_data)
                    self.edge_devices[device_config.device_id] = device_config
                
                self.logger.info(f"Loaded {len(self.camera_configs)} camera configs and {len(self.edge_devices)} edge device configs")
            
        except Exception as e:
            self.logger.error(f"Failed to load configurations: {e}")
    
    def _save_configurations(self):
        """Save configurations to file."""
        try:
            data = {
                "cameras": [self._camera_config_to_dict(config) for config in self.camera_configs.values()],
                "edge_devices": [self._edge_device_config_to_dict(config) for config in self.edge_devices.values()]
            }
            
            with open(self.config_file_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.logger.info("Configurations saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save configurations: {e}")
    
    def _setup_default_configurations(self):
        """Setup default camera and edge device configurations."""
        # Default gate camera
        gate_camera = CameraConfigExtended(
            camera_id="gate_camera",
            camera_type=CameraType.USB_CAMERA,
            location=CameraLocation.GATE,
            source="0",  # First USB camera
            resolution=(1280, 720),
            fps=30,
            detection_confidence=0.8,  # Higher confidence for gate
            edge_processing_enabled=True
        )
        
        # Default classroom camera
        classroom_camera = CameraConfigExtended(
            camera_id="classroom_camera",
            camera_type=CameraType.USB_CAMERA,
            location=CameraLocation.CLASSROOM,
            source="1",  # Second USB camera
            resolution=(1920, 1080),
            fps=30,
            detection_confidence=0.7,
            edge_processing_enabled=True
        )
        
        # Default edge device
        edge_device = EdgeDeviceConfig(
            device_id="main_edge_device",
            device_type=EdgeDeviceType.NVIDIA_JETSON_NANO,
            ip_address="localhost",
            port=8080,
            max_concurrent_streams=2,
            hardware_acceleration=True
        )
        
        # Add configurations
        self.add_camera_config(gate_camera)
        self.add_camera_config(classroom_camera)
        self.add_edge_device_config(edge_device)
        
        # Save default configurations
        self._save_configurations()
        
        self.logger.info("Default configurations created")
    
    def add_camera_config(self, config: CameraConfigExtended) -> bool:
        """Add a new camera configuration."""
        try:
            if config.camera_id in self.camera_configs:
                self.logger.warning(f"Camera config {config.camera_id} already exists")
                return False
            
            self.camera_configs[config.camera_id] = config
            self._save_configurations()
            
            self.logger.info(f"Added camera config: {config.camera_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add camera config: {e}")
            return False
    
    def update_camera_config(self, camera_id: str, config: CameraConfigExtended) -> bool:
        """Update existing camera configuration."""
        try:
            if camera_id not in self.camera_configs:
                self.logger.error(f"Camera config {camera_id} not found")
                return False
            
            self.camera_configs[camera_id] = config
            self._save_configurations()
            
            self.logger.info(f"Updated camera config: {camera_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update camera config: {e}")
            return False
    
    def remove_camera_config(self, camera_id: str) -> bool:
        """Remove camera configuration."""
        try:
            if camera_id not in self.camera_configs:
                self.logger.warning(f"Camera config {camera_id} not found")
                return False
            
            del self.camera_configs[camera_id]
            self._save_configurations()
            
            self.logger.info(f"Removed camera config: {camera_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove camera config: {e}")
            return False
    
    def get_camera_config(self, camera_id: str) -> Optional[CameraConfigExtended]:
        """Get camera configuration by ID."""
        return self.camera_configs.get(camera_id)
    
    def get_all_camera_configs(self) -> Dict[str, CameraConfigExtended]:
        """Get all camera configurations."""
        return self.camera_configs.copy()
    
    def get_cameras_by_location(self, location: CameraLocation) -> List[CameraConfigExtended]:
        """Get cameras by location."""
        return [config for config in self.camera_configs.values() if config.location == location]
    
    def get_cameras_by_type(self, camera_type: CameraType) -> List[CameraConfigExtended]:
        """Get cameras by type."""
        return [config for config in self.camera_configs.values() if config.camera_type == camera_type]
    
    def add_edge_device_config(self, config: EdgeDeviceConfig) -> bool:
        """Add edge device configuration."""
        try:
            if config.device_id in self.edge_devices:
                self.logger.warning(f"Edge device config {config.device_id} already exists")
                return False
            
            self.edge_devices[config.device_id] = config
            self._save_configurations()
            
            self.logger.info(f"Added edge device config: {config.device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add edge device config: {e}")
            return False
    
    def update_edge_device_config(self, device_id: str, config: EdgeDeviceConfig) -> bool:
        """Update edge device configuration."""
        try:
            if device_id not in self.edge_devices:
                self.logger.error(f"Edge device config {device_id} not found")
                return False
            
            self.edge_devices[device_id] = config
            self._save_configurations()
            
            self.logger.info(f"Updated edge device config: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update edge device config: {e}")
            return False
    
    def get_edge_device_config(self, device_id: str) -> Optional[EdgeDeviceConfig]:
        """Get edge device configuration by ID."""
        return self.edge_devices.get(device_id)
    
    def get_all_edge_device_configs(self) -> Dict[str, EdgeDeviceConfig]:
        """Get all edge device configurations."""
        return self.edge_devices.copy()
    
    def get_camera_configs_for_service(self) -> List[CameraConfig]:
        """Get camera configurations formatted for camera service."""
        return [config.to_camera_config() for config in self.camera_configs.values()]
    
    def validate_camera_config(self, config: CameraConfigExtended) -> List[str]:
        """Validate camera configuration and return list of issues."""
        issues = []
        
        # Basic validation
        if not config.camera_id:
            issues.append("Camera ID is required")
        
        if not config.source:
            issues.append("Camera source is required")
        
        # Resolution validation
        if config.resolution[0] < 640 or config.resolution[1] < 480:
            issues.append("Resolution too low (minimum 640x480)")
        
        # FPS validation
        if config.fps < 1 or config.fps > 60:
            issues.append("FPS must be between 1 and 60")
        
        # Network camera validation
        if config.camera_type in [CameraType.IP_CAMERA, CameraType.RTSP_STREAM, CameraType.HTTP_STREAM]:
            if not config.source.startswith(('http://', 'https://', 'rtsp://')):
                issues.append("Network camera source must be a valid URL")
        
        # Edge device validation
        if config.edge_processing_enabled and not config.edge_device_id:
            issues.append("Edge device ID required when edge processing is enabled")
        
        if config.edge_device_id and config.edge_device_id not in self.edge_devices:
            issues.append(f"Edge device {config.edge_device_id} not found")
        
        return issues
    
    def validate_edge_device_config(self, config: EdgeDeviceConfig) -> List[str]:
        """Validate edge device configuration and return list of issues."""
        issues = []
        
        # Basic validation
        if not config.device_id:
            issues.append("Device ID is required")
        
        if not config.ip_address:
            issues.append("IP address is required")
        
        # Port validation
        if config.port < 1 or config.port > 65535:
            issues.append("Port must be between 1 and 65535")
        
        # Resource limits validation
        if config.memory_limit_mb < 512:
            issues.append("Memory limit too low (minimum 512MB)")
        
        if config.cpu_limit_percent < 10 or config.cpu_limit_percent > 100:
            issues.append("CPU limit must be between 10% and 100%")
        
        return issues
    
    def create_ip_camera_config(
        self,
        camera_id: str,
        ip_address: str,
        location: CameraLocation,
        username: Optional[str] = None,
        password: Optional[str] = None,
        port: int = 554,
        stream_path: str = "/stream"
    ) -> CameraConfigExtended:
        """Create IP camera configuration."""
        
        # Build RTSP URL
        if username and password:
            source = f"rtsp://{username}:{password}@{ip_address}:{port}{stream_path}"
        else:
            source = f"rtsp://{ip_address}:{port}{stream_path}"
        
        return CameraConfigExtended(
            camera_id=camera_id,
            camera_type=CameraType.RTSP_STREAM,
            location=location,
            source=source,
            username=username,
            password=password,
            timeout=30
        )
    
    def create_usb_camera_config(
        self,
        camera_id: str,
        device_index: int,
        location: CameraLocation,
        resolution: tuple = (1280, 720)
    ) -> CameraConfigExtended:
        """Create USB camera configuration."""
        
        return CameraConfigExtended(
            camera_id=camera_id,
            camera_type=CameraType.USB_CAMERA,
            location=location,
            source=str(device_index),
            resolution=resolution
        )
    
    def _dict_to_camera_config(self, data: dict) -> CameraConfigExtended:
        """Convert dictionary to CameraConfigExtended."""
        # Handle enum conversions
        data["camera_type"] = CameraType(data["camera_type"])
        data["location"] = CameraLocation(data["location"])
        data["resolution"] = tuple(data["resolution"])
        
        return CameraConfigExtended(**data)
    
    def _camera_config_to_dict(self, config: CameraConfigExtended) -> dict:
        """Convert CameraConfigExtended to dictionary."""
        data = asdict(config)
        data["camera_type"] = config.camera_type.value
        data["location"] = config.location.value
        return data
    
    def _dict_to_edge_device_config(self, data: dict) -> EdgeDeviceConfig:
        """Convert dictionary to EdgeDeviceConfig."""
        data["device_type"] = EdgeDeviceType(data["device_type"])
        return EdgeDeviceConfig(**data)
    
    def _edge_device_config_to_dict(self, config: EdgeDeviceConfig) -> dict:
        """Convert EdgeDeviceConfig to dictionary."""
        data = asdict(config)
        data["device_type"] = config.device_type.value
        return data
    
    def get_system_info(self) -> dict:
        """Get system information for camera configuration."""
        return {
            "total_cameras": len(self.camera_configs),
            "cameras_by_location": {
                "gate": len(self.get_cameras_by_location(CameraLocation.GATE)),
                "classroom": len(self.get_cameras_by_location(CameraLocation.CLASSROOM))
            },
            "cameras_by_type": {
                camera_type.value: len(self.get_cameras_by_type(camera_type))
                for camera_type in CameraType
            },
            "total_edge_devices": len(self.edge_devices),
            "edge_devices_by_type": {
                device_type.value: len([d for d in self.edge_devices.values() if d.device_type == device_type])
                for device_type in EdgeDeviceType
            },
            "edge_processing_enabled": len([c for c in self.camera_configs.values() if c.edge_processing_enabled])
        }
"""
Camera Service implementation for video streaming and multi-camera support.

This service handles camera connections, video stream processing, frame buffering,
and coordination between gate and classroom cameras.
"""

import cv2
import numpy as np
import threading
import queue
import time
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime
from enum import Enum
import logging

from backend.core.base_service import BaseCameraService
from backend.core.interfaces import ICameraService
from backend.models.face_detection import CameraLocation


class CameraStatus(Enum):
    """Camera connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    STREAMING = "streaming"


class CameraConfig:
    """Configuration for individual cameras."""
    
    def __init__(
        self,
        camera_id: str,
        location: CameraLocation,
        source: str,
        resolution: Tuple[int, int] = (1280, 720),
        fps: int = 30,
        buffer_size: int = 10,
        retry_attempts: int = 3,
        retry_delay: float = 5.0
    ):
        self.camera_id = camera_id
        self.location = location
        self.source = source  # Can be device index, IP camera URL, or file path
        self.resolution = resolution
        self.fps = fps
        self.buffer_size = buffer_size
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay


class CameraStream:
    """Individual camera stream handler."""
    
    def __init__(self, config: CameraConfig):
        self.config = config
        self.cap = None
        self.status = CameraStatus.DISCONNECTED
        self.frame_buffer = queue.Queue(maxsize=config.buffer_size)
        self.latest_frame = None
        self.frame_timestamp = None
        self.thread = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"CameraStream_{config.camera_id}")
        
        # Statistics
        self.stats = {
            "frames_captured": 0,
            "frames_dropped": 0,
            "connection_attempts": 0,
            "last_frame_time": None,
            "fps_actual": 0.0
        }
        
        # Frame rate calculation
        self.fps_counter = 0
        self.fps_start_time = time.time()
    
    def connect(self) -> bool:
        """Connect to camera source."""
        try:
            self.status = CameraStatus.CONNECTING
            self.stats["connection_attempts"] += 1
            
            # Determine source type and create VideoCapture
            if isinstance(self.config.source, int):
                # USB/built-in camera
                self.cap = cv2.VideoCapture(self.config.source)
            elif self.config.source.startswith(('http://', 'https://', 'rtsp://')):
                # IP camera
                self.cap = cv2.VideoCapture(self.config.source)
            else:
                # File or other source
                self.cap = cv2.VideoCapture(self.config.source)
            
            if not self.cap.isOpened():
                self.logger.error(f"Failed to open camera source: {self.config.source}")
                self.status = CameraStatus.ERROR
                return False
            
            # Configure camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.resolution[0])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.resolution[1])
            self.cap.set(cv2.CAP_PROP_FPS, self.config.fps)
            
            # Set buffer size to reduce latency
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Test frame capture
            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.logger.error("Failed to capture test frame")
                self.cap.release()
                self.status = CameraStatus.ERROR
                return False
            
            self.status = CameraStatus.CONNECTED
            self.logger.info(f"Camera {self.config.camera_id} connected successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Camera connection failed: {e}")
            self.status = CameraStatus.ERROR
            if self.cap:
                self.cap.release()
            return False
    
    def start_streaming(self) -> bool:
        """Start video streaming in a separate thread."""
        try:
            if self.status != CameraStatus.CONNECTED:
                if not self.connect():
                    return False
            
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._stream_loop, daemon=True)
            self.thread.start()
            
            self.status = CameraStatus.STREAMING
            self.logger.info(f"Camera {self.config.camera_id} streaming started")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start streaming: {e}")
            return False
    
    def stop_streaming(self):
        """Stop video streaming."""
        try:
            self.stop_event.set()
            
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5.0)
            
            if self.cap:
                self.cap.release()
            
            # Clear frame buffer
            while not self.frame_buffer.empty():
                try:
                    self.frame_buffer.get_nowait()
                except queue.Empty:
                    break
            
            self.status = CameraStatus.DISCONNECTED
            self.logger.info(f"Camera {self.config.camera_id} streaming stopped")
            
        except Exception as e:
            self.logger.error(f"Error stopping streaming: {e}")
    
    def _stream_loop(self):
        """Main streaming loop running in separate thread."""
        frame_interval = 1.0 / self.config.fps
        last_frame_time = 0
        
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                
                # Control frame rate
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.001)  # Small sleep to prevent busy waiting
                    continue
                
                ret, frame = self.cap.read()
                
                if not ret or frame is None:
                    self.logger.warning("Failed to capture frame, attempting reconnection")
                    if not self._attempt_reconnection():
                        break
                    continue
                
                # Update statistics
                self.stats["frames_captured"] += 1
                self.stats["last_frame_time"] = current_time
                last_frame_time = current_time
                
                # Calculate actual FPS
                self.fps_counter += 1
                if current_time - self.fps_start_time >= 1.0:
                    self.stats["fps_actual"] = self.fps_counter / (current_time - self.fps_start_time)
                    self.fps_counter = 0
                    self.fps_start_time = current_time
                
                # Update latest frame with thread safety
                with self.lock:
                    self.latest_frame = frame.copy()
                    self.frame_timestamp = current_time
                
                # Add to buffer (non-blocking)
                try:
                    self.frame_buffer.put_nowait((frame.copy(), current_time))
                except queue.Full:
                    # Remove oldest frame and add new one
                    try:
                        self.frame_buffer.get_nowait()
                        self.frame_buffer.put_nowait((frame.copy(), current_time))
                        self.stats["frames_dropped"] += 1
                    except queue.Empty:
                        pass
                
            except Exception as e:
                self.logger.error(f"Error in streaming loop: {e}")
                time.sleep(0.1)
    
    def _attempt_reconnection(self) -> bool:
        """Attempt to reconnect to camera."""
        for attempt in range(self.config.retry_attempts):
            self.logger.info(f"Reconnection attempt {attempt + 1}/{self.config.retry_attempts}")
            
            if self.cap:
                self.cap.release()
            
            time.sleep(self.config.retry_delay)
            
            if self.connect():
                return True
        
        self.logger.error("All reconnection attempts failed")
        self.status = CameraStatus.ERROR
        return False
    
    def get_latest_frame(self) -> Optional[Tuple[np.ndarray, float]]:
        """Get the most recent frame."""
        with self.lock:
            if self.latest_frame is not None:
                return self.latest_frame.copy(), self.frame_timestamp
        return None
    
    def get_buffered_frame(self) -> Optional[Tuple[np.ndarray, float]]:
        """Get frame from buffer (FIFO)."""
        try:
            return self.frame_buffer.get_nowait()
        except queue.Empty:
            return None
    
    def is_healthy(self) -> bool:
        """Check if camera stream is healthy."""
        if self.status != CameraStatus.STREAMING:
            return False
        
        # Check if we've received frames recently
        if self.stats["last_frame_time"]:
            time_since_last_frame = time.time() - self.stats["last_frame_time"]
            return time_since_last_frame < 5.0  # 5 seconds timeout
        
        return False
    
    def get_stats(self) -> dict:
        """Get camera stream statistics."""
        return {
            "camera_id": self.config.camera_id,
            "location": self.config.location.value,
            "status": self.status.value,
            "resolution": self.config.resolution,
            "configured_fps": self.config.fps,
            "actual_fps": self.stats["fps_actual"],
            "frames_captured": self.stats["frames_captured"],
            "frames_dropped": self.stats["frames_dropped"],
            "connection_attempts": self.stats["connection_attempts"],
            "buffer_size": self.frame_buffer.qsize(),
            "is_healthy": self.is_healthy()
        }


class CameraService(BaseCameraService, ICameraService):
    """Multi-camera management service."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.cameras: Dict[str, CameraStream] = {}
        self.frame_processors: Dict[str, List[Callable]] = {}
        self.monitoring_thread = None
        self.monitoring_stop_event = threading.Event()
        
        # Default camera configurations
        self._setup_default_cameras()
        
        # Start monitoring
        self._start_monitoring()
    
    def _setup_default_cameras(self):
        """Setup default camera configurations."""
        # Gate camera configuration
        gate_config = CameraConfig(
            camera_id="gate_camera",
            location=CameraLocation.GATE,
            source=0,  # Default to first USB camera
            resolution=(1280, 720),
            fps=30,
            buffer_size=10
        )
        
        # Classroom camera configuration  
        classroom_config = CameraConfig(
            camera_id="classroom_camera",
            location=CameraLocation.CLASSROOM,
            source=1,  # Default to second USB camera
            resolution=(1920, 1080),
            fps=30,
            buffer_size=15
        )
        
        # Add cameras
        self.add_camera(gate_config)
        self.add_camera(classroom_config)
    
    def add_camera(self, config: CameraConfig) -> bool:
        """Add a new camera to the system."""
        try:
            if config.camera_id in self.cameras:
                self.logger.warning(f"Camera {config.camera_id} already exists")
                return False
            
            camera_stream = CameraStream(config)
            self.cameras[config.camera_id] = camera_stream
            self.frame_processors[config.camera_id] = []
            
            self.logger.info(f"Camera {config.camera_id} added successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add camera {config.camera_id}: {e}")
            return False
    
    def remove_camera(self, camera_id: str) -> bool:
        """Remove a camera from the system."""
        try:
            if camera_id not in self.cameras:
                self.logger.warning(f"Camera {camera_id} not found")
                return False
            
            # Stop streaming if active
            self.stop_stream(camera_id)
            
            # Remove camera
            del self.cameras[camera_id]
            del self.frame_processors[camera_id]
            
            self.logger.info(f"Camera {camera_id} removed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove camera {camera_id}: {e}")
            return False
    
    def start_stream(self, camera_id: str) -> bool:
        """Start streaming for a specific camera."""
        try:
            if camera_id not in self.cameras:
                self.logger.error(f"Camera {camera_id} not found")
                return False
            
            camera = self.cameras[camera_id]
            success = camera.start_streaming()
            
            self._log_camera_event(camera_id, "streaming started", success)
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to start stream for {camera_id}: {e}")
            return False
    
    def stop_stream(self, camera_id: str) -> bool:
        """Stop streaming for a specific camera."""
        try:
            if camera_id not in self.cameras:
                self.logger.error(f"Camera {camera_id} not found")
                return False
            
            camera = self.cameras[camera_id]
            camera.stop_streaming()
            
            self._log_camera_event(camera_id, "streaming stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop stream for {camera_id}: {e}")
            return False
    
    def start_all_streams(self) -> bool:
        """Start streaming for all cameras."""
        success_count = 0
        
        for camera_id in self.cameras:
            if self.start_stream(camera_id):
                success_count += 1
        
        total_cameras = len(self.cameras)
        self.logger.info(f"Started {success_count}/{total_cameras} camera streams")
        
        return success_count == total_cameras
    
    def stop_all_streams(self):
        """Stop streaming for all cameras."""
        for camera_id in self.cameras:
            self.stop_stream(camera_id)
        
        self.logger.info("All camera streams stopped")
    
    def get_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """Get current frame from camera."""
        try:
            if camera_id not in self.cameras:
                return None
            
            camera = self.cameras[camera_id]
            frame_data = camera.get_latest_frame()
            
            if frame_data:
                frame, timestamp = frame_data
                return frame
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get frame from {camera_id}: {e}")
            return None
    
    def get_buffered_frame(self, camera_id: str) -> Optional[Tuple[np.ndarray, float]]:
        """Get frame from camera buffer."""
        try:
            if camera_id not in self.cameras:
                return None
            
            camera = self.cameras[camera_id]
            return camera.get_buffered_frame()
            
        except Exception as e:
            self.logger.error(f"Failed to get buffered frame from {camera_id}: {e}")
            return None
    
    def is_camera_connected(self, camera_id: str) -> bool:
        """Check if camera is connected."""
        if camera_id not in self.cameras:
            return False
        
        camera = self.cameras[camera_id]
        return camera.status in [CameraStatus.CONNECTED, CameraStatus.STREAMING]
    
    def is_camera_streaming(self, camera_id: str) -> bool:
        """Check if camera is actively streaming."""
        if camera_id not in self.cameras:
            return False
        
        camera = self.cameras[camera_id]
        return camera.status == CameraStatus.STREAMING
    
    def get_camera_stats(self, camera_id: str) -> Optional[dict]:
        """Get statistics for a specific camera."""
        if camera_id not in self.cameras:
            return None
        
        return self.cameras[camera_id].get_stats()
    
    def get_all_camera_stats(self) -> Dict[str, dict]:
        """Get statistics for all cameras."""
        stats = {}
        for camera_id, camera in self.cameras.items():
            stats[camera_id] = camera.get_stats()
        
        return stats
    
    def add_frame_processor(self, camera_id: str, processor: Callable[[np.ndarray], None]):
        """Add a frame processor for a specific camera."""
        if camera_id in self.frame_processors:
            self.frame_processors[camera_id].append(processor)
            self.logger.info(f"Frame processor added for camera {camera_id}")
    
    def remove_frame_processor(self, camera_id: str, processor: Callable[[np.ndarray], None]):
        """Remove a frame processor for a specific camera."""
        if camera_id in self.frame_processors:
            try:
                self.frame_processors[camera_id].remove(processor)
                self.logger.info(f"Frame processor removed for camera {camera_id}")
            except ValueError:
                self.logger.warning(f"Frame processor not found for camera {camera_id}")
    
    def process_frame(self, camera_id: str, frame: np.ndarray):
        """Process frame through registered processors."""
        if camera_id in self.frame_processors:
            for processor in self.frame_processors[camera_id]:
                try:
                    processor(frame)
                except Exception as e:
                    self.logger.error(f"Frame processor error for {camera_id}: {e}")
    
    def _start_monitoring(self):
        """Start camera monitoring thread."""
        self.monitoring_stop_event.clear()
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        self.logger.info("Camera monitoring started")
    
    def _monitoring_loop(self):
        """Monitor camera health and attempt reconnections."""
        while not self.monitoring_stop_event.is_set():
            try:
                for camera_id, camera in self.cameras.items():
                    if not camera.is_healthy() and camera.status == CameraStatus.STREAMING:
                        self.logger.warning(f"Camera {camera_id} appears unhealthy, attempting restart")
                        camera.stop_streaming()
                        time.sleep(2)
                        camera.start_streaming()
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(5)
    
    def shutdown(self):
        """Shutdown camera service."""
        self.logger.info("Shutting down camera service")
        
        # Stop monitoring
        self.monitoring_stop_event.set()
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5.0)
        
        # Stop all streams
        self.stop_all_streams()
        
        self.logger.info("Camera service shutdown complete")
    
    def health_check(self) -> dict:
        """Extended health check for camera service."""
        base_health = super().health_check()
        
        camera_health = {}
        healthy_cameras = 0
        
        for camera_id, camera in self.cameras.items():
            is_healthy = camera.is_healthy()
            camera_health[camera_id] = {
                "status": camera.status.value,
                "healthy": is_healthy,
                "fps": camera.stats.get("fps_actual", 0.0)
            }
            
            if is_healthy:
                healthy_cameras += 1
        
        base_health.update({
            "total_cameras": len(self.cameras),
            "healthy_cameras": healthy_cameras,
            "camera_details": camera_health,
            "overall_camera_health": healthy_cameras == len(self.cameras)
        })
        
        return base_health
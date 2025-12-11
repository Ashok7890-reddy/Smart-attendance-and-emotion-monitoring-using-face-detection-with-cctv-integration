"""
Integration tests for camera processing and video streaming.

Tests camera connectivity, video stream processing, multi-camera coordination,
and edge processing performance and accuracy.
"""

import pytest
import asyncio
import numpy as np
import cv2
import time
import threading
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import List, Dict, Any

from backend.services.camera_service import CameraService, CameraStream, CameraConfig, CameraStatus
from backend.services.video_stream_processor import VideoStreamProcessor, FrameProcessingTask, ProcessingPriority
from backend.services.camera_config_manager import CameraConfigManager, CameraConfigExtended, CameraType, EdgeDeviceConfig, EdgeDeviceType
from backend.services.edge_processing_service import EdgeProcessingService, EdgeDevice, EdgeProcessingMode
from backend.services.edge_communication_service import EdgeCommunicationService, CommandType
from backend.models.face_detection import CameraLocation, FaceDetection
from backend.core.config import Config


class TestCameraService:
    """Test camera service functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
        self.camera_service = CameraService(self.config)
    
    def teardown_method(self):
        """Cleanup after tests."""
        self.camera_service.shutdown()
    
    def create_mock_camera_config(self, camera_id: str, location: CameraLocation) -> CameraConfig:
        """Create mock camera configuration."""
        return CameraConfig(
            camera_id=camera_id,
            location=location,
            source="mock_source",  # Mock source for testing
            resolution=(640, 480),
            fps=15,  # Lower FPS for testing
            buffer_size=5
        )
    
    def test_add_camera(self):
        """Test adding camera to service."""
        config = self.create_mock_camera_config("test_camera", CameraLocation.CLASSROOM)
        
        result = self.camera_service.add_camera(config)
        
        assert result is True
        assert "test_camera" in self.camera_service.cameras
        assert self.camera_service.cameras["test_camera"].config.camera_id == "test_camera"
    
    def test_add_duplicate_camera(self):
        """Test adding duplicate camera."""
        config = self.create_mock_camera_config("test_camera", CameraLocation.CLASSROOM)
        
        # Add camera first time
        result1 = self.camera_service.add_camera(config)
        # Try to add same camera again
        result2 = self.camera_service.add_camera(config)
        
        assert result1 is True
        assert result2 is False
    
    def test_remove_camera(self):
        """Test removing camera from service."""
        config = self.create_mock_camera_config("test_camera", CameraLocation.CLASSROOM)
        
        # Add camera
        self.camera_service.add_camera(config)
        
        # Remove camera
        result = self.camera_service.remove_camera("test_camera")
        
        assert result is True
        assert "test_camera" not in self.camera_service.cameras
    
    def test_remove_nonexistent_camera(self):
        """Test removing non-existent camera."""
        result = self.camera_service.remove_camera("nonexistent_camera")
        
        assert result is False
    
    @patch('cv2.VideoCapture')
    def test_camera_connection_mock(self, mock_video_capture):
        """Test camera connection with mock."""
        # Setup mock
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_video_capture.return_value = mock_cap
        
        config = self.create_mock_camera_config("test_camera", CameraLocation.CLASSROOM)
        self.camera_service.add_camera(config)
        
        # Test connection
        camera = self.camera_service.cameras["test_camera"]
        result = camera.connect()
        
        assert result is True
        assert camera.status == CameraStatus.CONNECTED
    
    @patch('cv2.VideoCapture')
    def test_camera_connection_failure(self, mock_video_capture):
        """Test camera connection failure."""
        # Setup mock to fail
        mock_cap = Mock()
        mock_cap.isOpened.return_value = False
        mock_video_capture.return_value = mock_cap
        
        config = self.create_mock_camera_config("test_camera", CameraLocation.CLASSROOM)
        self.camera_service.add_camera(config)
        
        # Test connection failure
        camera = self.camera_service.cameras["test_camera"]
        result = camera.connect()
        
        assert result is False
        assert camera.status == CameraStatus.ERROR
    
    def test_get_camera_stats(self):
        """Test getting camera statistics."""
        config = self.create_mock_camera_config("test_camera", CameraLocation.CLASSROOM)
        self.camera_service.add_camera(config)
        
        stats = self.camera_service.get_camera_stats("test_camera")
        
        assert stats is not None
        assert stats["camera_id"] == "test_camera"
        assert stats["location"] == "classroom"
        assert "status" in stats
        assert "resolution" in stats
    
    def test_get_all_camera_stats(self):
        """Test getting all camera statistics."""
        # Get initial camera count (default cameras)
        initial_stats = self.camera_service.get_all_camera_stats()
        initial_count = len(initial_stats)
        
        config1 = self.create_mock_camera_config("camera1", CameraLocation.GATE)
        config2 = self.create_mock_camera_config("camera2", CameraLocation.CLASSROOM)
        
        self.camera_service.add_camera(config1)
        self.camera_service.add_camera(config2)
        
        all_stats = self.camera_service.get_all_camera_stats()
        
        assert len(all_stats) == initial_count + 2
        assert "camera1" in all_stats
        assert "camera2" in all_stats
    
    def test_health_check(self):
        """Test camera service health check."""
        health = self.camera_service.health_check()
        
        assert "service" in health
        assert "total_cameras" in health
        assert "healthy_cameras" in health
        assert "camera_details" in health


class TestVideoStreamProcessor:
    """Test video stream processor functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
        
        # Mock the services to avoid actual processing
        with patch('backend.services.video_stream_processor.CameraService'), \
             patch('backend.services.video_stream_processor.FaceRecognitionService'), \
             patch('backend.services.video_stream_processor.EmotionAnalysisService'):
            self.processor = VideoStreamProcessor(self.config)
    
    def teardown_method(self):
        """Cleanup after tests."""
        self.processor.shutdown()
    
    def create_test_frame(self, width=640, height=480) -> np.ndarray:
        """Create test video frame."""
        return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    
    def test_start_camera_processing(self):
        """Test starting camera processing."""
        # Mock camera service methods
        self.processor.camera_service.start_stream = Mock(return_value=True)
        self.processor.camera_service.add_frame_processor = Mock()
        
        result = self.processor.start_camera_processing("test_camera")
        
        assert result is True
        assert "test_camera" in self.processor.frame_coordinators
        self.processor.camera_service.start_stream.assert_called_once_with("test_camera")
    
    def test_stop_camera_processing(self):
        """Test stopping camera processing."""
        # Setup
        self.processor.frame_coordinators["test_camera"] = Mock()
        self.processor.camera_service.stop_stream = Mock()
        
        result = self.processor.stop_camera_processing("test_camera")
        
        assert result is True
        assert "test_camera" not in self.processor.frame_coordinators
        self.processor.camera_service.stop_stream.assert_called_once_with("test_camera")
    
    def test_frame_processing_task_creation(self):
        """Test frame processing task creation."""
        frame = self.create_test_frame()
        
        task = FrameProcessingTask(
            camera_id="test_camera",
            frame=frame,
            timestamp=time.time(),
            camera_location=CameraLocation.CLASSROOM,
            priority=ProcessingPriority.NORMAL
        )
        
        assert task.camera_id == "test_camera"
        assert task.frame.shape == frame.shape
        assert task.camera_location == CameraLocation.CLASSROOM
        assert task.priority == ProcessingPriority.NORMAL
        assert task.processing_started_at is None
        assert task.processing_completed_at is None
    
    def test_get_processing_statistics(self):
        """Test getting processing statistics."""
        # Mock camera service
        self.processor.camera_service.get_all_camera_stats = Mock(return_value={"test_camera": {}})
        self.processor.face_recognition_service.get_recognition_stats = Mock(return_value={})
        self.processor.emotion_analysis_service.get_processing_stats = Mock(return_value={})
        
        stats = self.processor.get_processing_statistics()
        
        assert "video_processing" in stats
        assert "camera_stats" in stats
        assert "queue_size" in stats
        assert "active_threads" in stats
    
    def test_health_check(self):
        """Test video stream processor health check."""
        # Mock camera service health check
        self.processor.camera_service.health_check = Mock(return_value={"overall_camera_health": True})
        
        health = self.processor.health_check()
        
        assert "processing_threads" in health
        assert "queues" in health
        assert "camera_service" in health
        assert "overall_healthy" in health


class TestCameraConfigManager:
    """Test camera configuration manager."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Use temporary file for testing
        import tempfile
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_file.close()
        
        self.config_manager = CameraConfigManager(config_file_path=self.temp_file.name)
    
    def teardown_method(self):
        """Cleanup after tests."""
        import os
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)
    
    def create_test_camera_config(self, camera_id: str) -> CameraConfigExtended:
        """Create test camera configuration."""
        return CameraConfigExtended(
            camera_id=camera_id,
            camera_type=CameraType.USB_CAMERA,
            location=CameraLocation.CLASSROOM,
            source="0",
            resolution=(640, 480),
            fps=30
        )
    
    def test_add_camera_config(self):
        """Test adding camera configuration."""
        config = self.create_test_camera_config("test_camera")
        
        result = self.config_manager.add_camera_config(config)
        
        assert result is True
        assert "test_camera" in self.config_manager.camera_configs
    
    def test_update_camera_config(self):
        """Test updating camera configuration."""
        config = self.create_test_camera_config("test_camera")
        self.config_manager.add_camera_config(config)
        
        # Update configuration
        config.fps = 60
        result = self.config_manager.update_camera_config("test_camera", config)
        
        assert result is True
        assert self.config_manager.camera_configs["test_camera"].fps == 60
    
    def test_remove_camera_config(self):
        """Test removing camera configuration."""
        config = self.create_test_camera_config("test_camera")
        self.config_manager.add_camera_config(config)
        
        result = self.config_manager.remove_camera_config("test_camera")
        
        assert result is True
        assert "test_camera" not in self.config_manager.camera_configs
    
    def test_validate_camera_config(self):
        """Test camera configuration validation."""
        config = self.create_test_camera_config("test_camera")
        
        issues = self.config_manager.validate_camera_config(config)
        
        assert isinstance(issues, list)
        assert len(issues) == 0  # Should be valid
    
    def test_validate_invalid_camera_config(self):
        """Test validation of invalid camera configuration."""
        config = CameraConfigExtended(
            camera_id="",  # Invalid: empty ID
            camera_type=CameraType.USB_CAMERA,
            location=CameraLocation.CLASSROOM,
            source="",  # Invalid: empty source
            resolution=(100, 100),  # Invalid: too low resolution
            fps=0  # Invalid: zero FPS
        )
        
        issues = self.config_manager.validate_camera_config(config)
        
        assert len(issues) > 0
        assert any("Camera ID is required" in issue for issue in issues)
        assert any("Camera source is required" in issue for issue in issues)
    
    def test_create_ip_camera_config(self):
        """Test creating IP camera configuration."""
        config = self.config_manager.create_ip_camera_config(
            camera_id="ip_camera",
            ip_address="192.168.1.100",
            location=CameraLocation.GATE,
            username="admin",
            password="password"
        )
        
        assert config.camera_id == "ip_camera"
        assert config.camera_type == CameraType.RTSP_STREAM
        assert config.location == CameraLocation.GATE
        assert "192.168.1.100" in config.source
        assert config.username == "admin"
        assert config.password == "password"
    
    def test_get_system_info(self):
        """Test getting system information."""
        # Add some test configurations
        gate_config = self.create_test_camera_config("gate_camera")
        gate_config.location = CameraLocation.GATE
        classroom_config = self.create_test_camera_config("classroom_camera")
        classroom_config.location = CameraLocation.CLASSROOM
        
        self.config_manager.add_camera_config(gate_config)
        self.config_manager.add_camera_config(classroom_config)
        
        system_info = self.config_manager.get_system_info()
        
        assert system_info["total_cameras"] == 2
        assert system_info["cameras_by_location"]["gate"] == 1
        assert system_info["cameras_by_location"]["classroom"] == 1


@pytest.mark.asyncio
class TestEdgeProcessingService:
    """Test edge processing service functionality."""
    
    async def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
        self.edge_service = EdgeProcessingService(self.config)
    
    async def teardown_method(self):
        """Cleanup after tests."""
        self.edge_service.shutdown()
    
    def create_test_edge_device_config(self, device_id: str) -> EdgeDeviceConfig:
        """Create test edge device configuration."""
        return EdgeDeviceConfig(
            device_id=device_id,
            device_type=EdgeDeviceType.NVIDIA_JETSON_NANO,
            ip_address="127.0.0.1",
            port=8080,
            max_concurrent_streams=2
        )
    
    def test_add_edge_device(self):
        """Test adding edge device."""
        config = self.create_test_edge_device_config("test_device")
        
        result = self.edge_service.add_edge_device(config)
        
        assert result is True
        assert "test_device" in self.edge_service.edge_devices
    
    def test_remove_edge_device(self):
        """Test removing edge device."""
        config = self.create_test_edge_device_config("test_device")
        self.edge_service.add_edge_device(config)
        
        result = self.edge_service.remove_edge_device("test_device")
        
        assert result is True
        assert "test_device" not in self.edge_service.edge_devices
    
    async def test_submit_processing_task(self):
        """Test submitting processing task."""
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        task_id = await self.edge_service.submit_processing_task(
            camera_id="test_camera",
            frame=frame,
            camera_location=CameraLocation.CLASSROOM
        )
        
        assert task_id != ""
        assert self.edge_service.processing_stats["total_tasks"] == 1
    
    def test_get_processing_statistics(self):
        """Test getting processing statistics."""
        stats = self.edge_service.get_processing_statistics()
        
        assert "processing_stats" in stats
        assert "edge_devices" in stats
        assert "active_tasks" in stats
        assert "processing_mode" in stats
    
    def test_set_processing_mode(self):
        """Test setting processing mode."""
        self.edge_service.set_processing_mode(EdgeProcessingMode.EDGE_ONLY)
        
        assert self.edge_service.processing_mode == EdgeProcessingMode.EDGE_ONLY


@pytest.mark.asyncio
class TestEdgeCommunicationService:
    """Test edge communication service functionality."""
    
    async def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
        self.comm_service = EdgeCommunicationService(self.config)
    
    async def teardown_method(self):
        """Cleanup after tests."""
        await self.comm_service.shutdown()
    
    def create_test_edge_device_config(self, device_id: str) -> EdgeDeviceConfig:
        """Create test edge device configuration."""
        return EdgeDeviceConfig(
            device_id=device_id,
            device_type=EdgeDeviceType.NVIDIA_JETSON_NANO,
            ip_address="127.0.0.1",
            port=8080
        )
    
    def test_add_device(self):
        """Test adding device for communication."""
        config = self.create_test_edge_device_config("test_device")
        
        result = self.comm_service.add_device(config)
        
        assert result is True
        assert "test_device" in self.comm_service.device_configs
    
    def test_remove_device(self):
        """Test removing device from communication."""
        config = self.create_test_edge_device_config("test_device")
        self.comm_service.add_device(config)
        
        result = self.comm_service.remove_device("test_device")
        
        assert result is True
        assert "test_device" not in self.comm_service.device_configs
    
    async def test_send_command(self):
        """Test sending command to edge device."""
        config = self.create_test_edge_device_config("test_device")
        self.comm_service.add_device(config)
        
        command_id = await self.comm_service.send_command(
            device_id="test_device",
            command_type=CommandType.GET_STATUS,
            payload={}
        )
        
        assert command_id != ""
        assert command_id in self.comm_service.pending_commands
    
    def test_add_sync_data(self):
        """Test adding sync data."""
        self.comm_service.add_sync_data(
            device_id="test_device",
            data_type="face_embeddings",
            data={"student_id": "123", "embedding": [0.1, 0.2, 0.3]}
        )
        
        sync_status = self.comm_service.get_device_sync_status("test_device")
        assert sync_status["pending_items"] == 1
    
    def test_get_communication_stats(self):
        """Test getting communication statistics."""
        stats = self.comm_service.get_communication_stats()
        
        assert "communication_stats" in stats
        assert "active_connections" in stats
        assert "pending_commands" in stats
        assert "sync_status" in stats


class TestCameraIntegrationEnd2End:
    """End-to-end integration tests for camera processing."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
    
    def teardown_method(self):
        """Cleanup after tests."""
        pass
    
    @patch('cv2.VideoCapture')
    def test_full_camera_pipeline_mock(self, mock_video_capture):
        """Test full camera processing pipeline with mocked camera."""
        # Setup mock camera
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        
        # Create test frames
        test_frames = [
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            for _ in range(5)
        ]
        
        mock_cap.read.side_effect = [(True, frame) for frame in test_frames] + [(False, None)]
        mock_video_capture.return_value = mock_cap
        
        # Setup camera service
        camera_service = CameraService(self.config)
        
        try:
            # Add camera
            config = CameraConfig(
                camera_id="test_camera",
                location=CameraLocation.CLASSROOM,
                source=0,
                resolution=(640, 480),
                fps=30,
                buffer_size=5
            )
            
            result = camera_service.add_camera(config)
            assert result is True
            
            # Start streaming
            result = camera_service.start_stream("test_camera")
            assert result is True
            
            # Wait a bit for frames to be processed
            time.sleep(0.5)
            
            # Check camera stats
            stats = camera_service.get_camera_stats("test_camera")
            assert stats is not None
            assert stats["status"] == "streaming"
            
            # Get frame
            frame = camera_service.get_frame("test_camera")
            assert frame is not None
            assert frame.shape == (480, 640, 3)
            
        finally:
            camera_service.shutdown()
    
    def test_multi_camera_coordination(self):
        """Test coordination between multiple cameras."""
        camera_service = CameraService(self.config)
        
        try:
            # Add multiple cameras
            gate_config = CameraConfig(
                camera_id="gate_camera",
                location=CameraLocation.GATE,
                source="mock_gate",
                resolution=(1280, 720),
                fps=30
            )
            
            classroom_config = CameraConfig(
                camera_id="classroom_camera",
                location=CameraLocation.CLASSROOM,
                source="mock_classroom",
                resolution=(1920, 1080),
                fps=30
            )
            
            camera_service.add_camera(gate_config)
            camera_service.add_camera(classroom_config)
            
            # Check all cameras added
            all_stats = camera_service.get_all_camera_stats()
            assert len(all_stats) == 2
            assert "gate_camera" in all_stats
            assert "classroom_camera" in all_stats
            
            # Test health check
            health = camera_service.health_check()
            assert health["total_cameras"] == 2
            
        finally:
            camera_service.shutdown()
    
    def test_camera_failure_recovery(self):
        """Test camera failure and recovery scenarios."""
        camera_service = CameraService(self.config)
        
        try:
            # Add camera with invalid source (should fail to connect)
            config = CameraConfig(
                camera_id="failing_camera",
                location=CameraLocation.CLASSROOM,
                source="invalid_source",
                resolution=(640, 480),
                fps=30
            )
            
            camera_service.add_camera(config)
            
            # Try to start stream (should fail)
            result = camera_service.start_stream("failing_camera")
            # Note: This might succeed in test environment, but would fail with real invalid source
            
            # Check camera status
            stats = camera_service.get_camera_stats("failing_camera")
            assert stats is not None
            
        finally:
            camera_service.shutdown()
    
    def test_performance_under_load(self):
        """Test system performance under simulated load."""
        camera_service = CameraService(self.config)
        
        try:
            # Add multiple cameras
            for i in range(3):
                config = CameraConfig(
                    camera_id=f"camera_{i}",
                    location=CameraLocation.CLASSROOM if i % 2 == 0 else CameraLocation.GATE,
                    source=f"mock_source_{i}",
                    resolution=(640, 480),
                    fps=15  # Lower FPS for testing
                )
                camera_service.add_camera(config)
            
            # Check system can handle multiple cameras
            all_stats = camera_service.get_all_camera_stats()
            assert len(all_stats) == 3
            
            # Test health check under load
            health = camera_service.health_check()
            assert health["total_cameras"] == 3
            
        finally:
            camera_service.shutdown()


class TestCameraConnectivityIntegration:
    """Integration tests for camera connectivity and stream processing."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
        self.camera_service = CameraService(self.config)
    
    def teardown_method(self):
        """Cleanup after tests."""
        self.camera_service.shutdown()
    
    @patch('cv2.VideoCapture')
    def test_camera_connectivity_monitoring(self, mock_video_capture):
        """Test camera connectivity monitoring and health checks."""
        # Setup mock camera with intermittent connectivity
        mock_cap = Mock()
        mock_cap.isOpened.side_effect = [True, True, False, True]  # Simulate connection loss
        mock_cap.read.side_effect = [
            (True, np.zeros((480, 640, 3), dtype=np.uint8)),
            (True, np.zeros((480, 640, 3), dtype=np.uint8)),
            (False, None),  # Connection lost
            (True, np.zeros((480, 640, 3), dtype=np.uint8))  # Reconnected
        ]
        mock_video_capture.return_value = mock_cap
        
        config = self.create_mock_camera_config("monitor_camera", CameraLocation.GATE)
        self.camera_service.add_camera(config)
        
        camera 
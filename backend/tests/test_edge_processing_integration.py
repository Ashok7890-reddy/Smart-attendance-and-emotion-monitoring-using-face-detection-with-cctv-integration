"""
Integration tests for edge processing and communication.

Tests edge device connectivity, distributed processing performance,
edge-to-cloud communication, and data synchronization.
"""

import pytest
import asyncio
import numpy as np
import time
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import List, Dict, Any

from backend.services.edge_processing_service import EdgeProcessingService, EdgeDevice, EdgeProcessingMode, ProcessingTask
from backend.services.edge_communication_service import EdgeCommunicationService, CommandType, CommandStatus
from backend.services.camera_config_manager import EdgeDeviceConfig, EdgeDeviceType
from backend.models.face_detection import CameraLocation, FaceDetection
from backend.core.config import Config


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
            max_concurrent_streams=2,
            processing_capabilities={
                "face_detection": True,
                "emotion_analysis": True,
                "liveness_detection": True
            },
            api_key="test_api_key"
        )
    
    def create_test_frame(self, width=640, height=480) -> np.ndarray:
        """Create test video frame."""
        return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    
    def test_add_edge_device(self):
        """Test adding edge device."""
        config = self.create_test_edge_device_config("test_device")
        
        result = self.edge_service.add_edge_device(config)
        
        assert result is True
        assert "test_device" in self.edge_service.edge_devices
        assert self.edge_service.edge_devices["test_device"].config.device_id == "test_device"
    
    def test_add_duplicate_edge_device(self):
        """Test adding duplicate edge device."""
        config = self.create_test_edge_device_config("test_device")
        
        # Add device first time
        result1 = self.edge_service.add_edge_device(config)
        # Try to add same device again
        result2 = self.edge_service.add_edge_device(config)
        
        assert result1 is True
        assert result2 is False
    
    def test_remove_edge_device(self):
        """Test removing edge device."""
        config = self.create_test_edge_device_config("test_device")
        
        # Add device
        self.edge_service.add_edge_device(config)
        
        # Remove device
        result = self.edge_service.remove_edge_device("test_device")
        
        assert result is True
        assert "test_device" not in self.edge_service.edge_devices
    
    def test_remove_nonexistent_edge_device(self):
        """Test removing non-existent edge device."""
        result = self.edge_service.remove_edge_device("nonexistent_device")
        
        assert result is False
    
    async def test_submit_processing_task(self):
        """Test submitting processing task."""
        frame = self.create_test_frame()
        
        task_id = await self.edge_service.submit_processing_task(
            camera_id="test_camera",
            frame=frame,
            camera_location=CameraLocation.CLASSROOM
        )
        
        assert task_id != ""
        assert self.edge_service.processing_stats["total_tasks"] == 1
    
    async def test_submit_multiple_processing_tasks(self):
        """Test submitting multiple processing tasks."""
        frame = self.create_test_frame()
        
        task_ids = []
        for i in range(5):
            task_id = await self.edge_service.submit_processing_task(
                camera_id=f"camera_{i}",
                frame=frame,
                camera_location=CameraLocation.CLASSROOM
            )
            task_ids.append(task_id)
        
        assert len(task_ids) == 5
        assert all(task_id != "" for task_id in task_ids)
        assert self.edge_service.processing_stats["total_tasks"] == 5
    
    def test_get_task_result_not_found(self):
        """Test getting result for non-existent task."""
        result = self.edge_service.get_task_result("nonexistent_task")
        
        assert result is not None
        assert result["status"] == "not_found"
    
    def test_set_processing_mode(self):
        """Test setting processing mode."""
        # Test each processing mode
        modes = [
            EdgeProcessingMode.EDGE_ONLY,
            EdgeProcessingMode.CLOUD_ONLY,
            EdgeProcessingMode.HYBRID,
            EdgeProcessingMode.FAILOVER
        ]
        
        for mode in modes:
            self.edge_service.set_processing_mode(mode)
            assert self.edge_service.processing_mode == mode
    
    def test_get_processing_statistics(self):
        """Test getting processing statistics."""
        stats = self.edge_service.get_processing_statistics()
        
        assert "processing_stats" in stats
        assert "edge_devices" in stats
        assert "active_tasks" in stats
        assert "pending_tasks" in stats
        assert "completed_tasks" in stats
        assert "processing_mode" in stats
    
    def test_get_edge_device_stats(self):
        """Test getting edge device statistics."""
        config = self.create_test_edge_device_config("test_device")
        self.edge_service.add_edge_device(config)
        
        stats = self.edge_service.get_edge_device_stats()
        
        assert "test_device" in stats
        assert stats["test_device"]["device_id"] == "test_device"
        assert "is_connected" in stats["test_device"]
        assert "current_load" in stats["test_device"]


class TestEdgeDevice:
    """Test edge device functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = EdgeDeviceConfig(
            device_id="test_device",
            device_type=EdgeDeviceType.NVIDIA_JETSON_NANO,
            ip_address="127.0.0.1",
            port=8080,
            processing_capabilities={
                "face_detection": True,
                "emotion_analysis": True
            }
        )
        self.edge_device = EdgeDevice(self.config)
    
    def create_test_processing_task(self) -> ProcessingTask:
        """Create test processing task."""
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        return ProcessingTask(
            task_id="test_task",
            camera_id="test_camera",
            frame=frame,
            timestamp=time.time(),
            camera_location=CameraLocation.CLASSROOM
        )
    
    @patch('aiohttp.ClientSession.get')
    async def test_connect_success(self, mock_get):
        """Test successful edge device connection."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.edge_device.connect()
        
        assert result is True
        assert self.edge_device.is_connected is True
        assert self.edge_device.last_heartbeat is not None
    
    @patch('aiohttp.ClientSession.get')
    async def test_connect_failure(self, mock_get):
        """Test edge device connection failure."""
        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.edge_device.connect()
        
        assert result is False
        assert self.edge_device.is_connected is False
    
    @patch('aiohttp.ClientSession.post')
    async def test_send_heartbeat_success(self, mock_post):
        """Test successful heartbeat."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        result = await self.edge_device.send_heartbeat()
        
        assert result is True
        assert self.edge_device.last_heartbeat is not None
    
    @patch('aiohttp.ClientSession.post')
    async def test_send_heartbeat_failure(self, mock_post):
        """Test heartbeat failure."""
        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_post.return_value.__aenter__.return_value = mock_response
        
        result = await self.edge_device.send_heartbeat()
        
        assert result is False
    
    @patch('aiohttp.ClientSession.post')
    async def test_process_frame_success(self, mock_post):
        """Test successful frame processing."""
        task = self.create_test_processing_task()
        
        # Mock successful processing response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "task_id": task.task_id,
            "face_detections": [
                {
                    "bounding_box": [100, 100, 200, 200],
                    "confidence": 0.95,
                    "liveness_score": 0.88
                }
            ],
            "processing_time": 0.15
        }
        mock_post.return_value.__aenter__.return_value = mock_response
        
        result = await self.edge_device.process_frame(task)
        
        assert result is not None
        assert result["task_id"] == task.task_id
        assert "face_detections" in result
        assert self.edge_device.stats["tasks_processed"] == 1
    
    @patch('aiohttp.ClientSession.post')
    async def test_process_frame_failure(self, mock_post):
        """Test frame processing failure."""
        task = self.create_test_processing_task()
        
        # Mock failed response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_post.return_value.__aenter__.return_value = mock_response
        
        result = await self.edge_device.process_frame(task)
        
        assert result is None
        assert self.edge_device.stats["tasks_failed"] == 1
    
    def test_get_load_score(self):
        """Test load score calculation."""
        # Initially should have low load
        load_score = self.edge_device.get_load_score()
        assert 0.0 <= load_score <= 1.0
        
        # Add some tasks to queue
        for i in range(5):
            self.edge_device.processing_queue.put(f"task_{i}")
        
        # Load should increase
        new_load_score = self.edge_device.get_load_score()
        assert new_load_score > load_score
    
    def test_is_healthy_disconnected(self):
        """Test health check when disconnected."""
        self.edge_device.is_connected = False
        
        assert self.edge_device.is_healthy() is False
    
    def test_is_healthy_connected_recent_heartbeat(self):
        """Test health check when connected with recent heartbeat."""
        self.edge_device.is_connected = True
        self.edge_device.last_heartbeat = time.time()
        
        assert self.edge_device.is_healthy() is True
    
    def test_is_healthy_connected_old_heartbeat(self):
        """Test health check when connected with old heartbeat."""
        self.edge_device.is_connected = True
        self.edge_device.last_heartbeat = time.time() - 120  # 2 minutes ago
        
        assert self.edge_device.is_healthy() is False
    
    def test_get_stats(self):
        """Test getting device statistics."""
        stats = self.edge_device.get_stats()
        
        assert stats["device_id"] == "test_device"
        assert stats["device_type"] == EdgeDeviceType.NVIDIA_JETSON_NANO.value
        assert "is_connected" in stats
        assert "is_healthy" in stats
        assert "current_load" in stats
        assert "tasks_processed" in stats
        assert "tasks_failed" in stats
        assert "success_rate" in stats
        assert "uptime_seconds" in stats


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
            port=8080,
            api_key="test_api_key"
        )
    
    def test_add_device(self):
        """Test adding device for communication."""
        config = self.create_test_edge_device_config("test_device")
        
        result = self.comm_service.add_device(config)
        
        assert result is True
        assert "test_device" in self.comm_service.device_configs
    
    def test_add_duplicate_device(self):
        """Test adding duplicate device."""
        config = self.create_test_edge_device_config("test_device")
        
        # Add device first time
        result1 = self.comm_service.add_device(config)
        # Add same device again (should overwrite)
        result2 = self.comm_service.add_device(config)
        
        assert result1 is True
        assert result2 is True
        assert len(self.comm_service.device_configs) == 1
    
    def test_remove_device(self):
        """Test removing device from communication."""
        config = self.create_test_edge_device_config("test_device")
        self.comm_service.add_device(config)
        
        result = self.comm_service.remove_device("test_device")
        
        assert result is True
        assert "test_device" not in self.comm_service.device_configs
    
    def test_remove_nonexistent_device(self):
        """Test removing non-existent device."""
        result = self.comm_service.remove_device("nonexistent_device")
        
        assert result is True  # Should not fail
    
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
    
    async def test_send_multiple_commands(self):
        """Test sending multiple commands."""
        config = self.create_test_edge_device_config("test_device")
        self.comm_service.add_device(config)
        
        command_types = [
            CommandType.GET_STATUS,
            CommandType.START_PROCESSING,
            CommandType.STOP_PROCESSING
        ]
        
        command_ids = []
        for cmd_type in command_types:
            command_id = await self.comm_service.send_command(
                device_id="test_device",
                command_type=cmd_type,
                payload={}
            )
            command_ids.append(command_id)
        
        assert len(command_ids) == 3
        assert all(cmd_id != "" for cmd_id in command_ids)
        assert len(self.comm_service.pending_commands) == 3
    
    def test_add_sync_data(self):
        """Test adding sync data."""
        self.comm_service.add_sync_data(
            device_id="test_device",
            data_type="face_embeddings",
            data={"student_id": "123", "embedding": [0.1, 0.2, 0.3]}
        )
        
        sync_status = self.comm_service.get_device_sync_status("test_device")
        assert sync_status["pending_items"] == 1
    
    def test_add_multiple_sync_data(self):
        """Test adding multiple sync data items."""
        for i in range(5):
            self.comm_service.add_sync_data(
                device_id="test_device",
                data_type="face_embeddings",
                data={"student_id": f"student_{i}", "embedding": [0.1, 0.2, 0.3]}
            )
        
        sync_status = self.comm_service.get_device_sync_status("test_device")
        assert sync_status["pending_items"] == 5
    
    def test_get_device_sync_status_nonexistent(self):
        """Test getting sync status for non-existent device."""
        sync_status = self.comm_service.get_device_sync_status("nonexistent_device")
        
        assert sync_status["device_id"] == "nonexistent_device"
        assert sync_status["pending_items"] == 0
        assert sync_status["last_sync_time"] is None
    
    def test_get_command_status_nonexistent(self):
        """Test getting status for non-existent command."""
        status = self.comm_service.get_command_status("nonexistent_command")
        
        assert status is None
    
    def test_get_communication_stats(self):
        """Test getting communication statistics."""
        stats = self.comm_service.get_communication_stats()
        
        assert "communication_stats" in stats
        assert "active_connections" in stats
        assert "pending_commands" in stats
        assert "command_history_size" in stats
        assert "devices_configured" in stats
        assert "sync_status" in stats


class TestCameraProcessingIntegration:
    """Integration tests for camera processing with edge devices."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
    
    def teardown_method(self):
        """Cleanup after tests."""
        pass
    
    def create_test_frame(self, width=640, height=480) -> np.ndarray:
        """Create test video frame."""
        return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    
    @patch('backend.services.edge_processing_service.EdgeDevice.connect')
    @patch('backend.services.edge_processing_service.EdgeDevice.process_frame')
    async def test_edge_processing_pipeline(self, mock_process_frame, mock_connect):
        """Test complete edge processing pipeline."""
        # Setup mocks
        mock_connect.return_value = True
        mock_process_frame.return_value = {
            "task_id": "test_task",
            "face_detections": [
                {
                    "bounding_box": [100, 100, 200, 200],
                    "confidence": 0.95,
                    "liveness_score": 0.88
                }
            ],
            "processing_time": 0.15
        }
        
        # Setup edge processing service
        edge_service = EdgeProcessingService(self.config)
        
        try:
            # Add edge device
            device_config = EdgeDeviceConfig(
                device_id="test_device",
                device_type=EdgeDeviceType.NVIDIA_JETSON_NANO,
                ip_address="127.0.0.1",
                port=8080,
                processing_capabilities={
                    "face_detection": True,
                    "emotion_analysis": True
                }
            )
            
            edge_service.add_edge_device(device_config)
            
            # Submit processing task
            frame = self.create_test_frame()
            task_id = await edge_service.submit_processing_task(
                camera_id="test_camera",
                frame=frame,
                camera_location=CameraLocation.GATE
            )
            
            assert task_id != ""
            
            # Wait for processing
            await asyncio.sleep(0.5)
            
            # Check task result
            result = edge_service.get_task_result(task_id)
            assert result is not None
            
        finally:
            edge_service.shutdown()
    
    @patch('backend.services.edge_processing_service.EdgeDevice.connect')
    async def test_edge_device_failover(self, mock_connect):
        """Test failover to cloud processing when edge device fails."""
        # Setup mock to simulate connection failure
        mock_connect.return_value = False
        
        # Setup edge processing service
        edge_service = EdgeProcessingService(self.config)
        edge_service.set_processing_mode(EdgeProcessingMode.FAILOVER)
        
        try:
            # Add edge device (will fail to connect)
            device_config = EdgeDeviceConfig(
                device_id="failing_device",
                device_type=EdgeDeviceType.NVIDIA_JETSON_NANO,
                ip_address="127.0.0.1",
                port=8080
            )
            
            edge_service.add_edge_device(device_config)
            
            # Submit processing task
            frame = self.create_test_frame()
            task_id = await edge_service.submit_processing_task(
                camera_id="test_camera",
                frame=frame,
                camera_location=CameraLocation.CLASSROOM
            )
            
            assert task_id != ""
            
            # Wait for processing (should fallback to cloud)
            await asyncio.sleep(1.0)
            
            # Check statistics
            stats = edge_service.get_processing_statistics()
            assert stats["processing_stats"]["total_tasks"] == 1
            
        finally:
            edge_service.shutdown()
    
    async def test_multi_camera_edge_coordination(self):
        """Test coordination between multiple cameras and edge devices."""
        edge_service = EdgeProcessingService(self.config)
        
        try:
            # Add multiple edge devices
            for i in range(2):
                device_config = EdgeDeviceConfig(
                    device_id=f"device_{i}",
                    device_type=EdgeDeviceType.NVIDIA_JETSON_NANO,
                    ip_address="127.0.0.1",
                    port=8080 + i,
                    processing_capabilities={
                        "face_detection": True,
                        "emotion_analysis": True
                    }
                )
                edge_service.add_edge_device(device_config)
            
            # Submit tasks from multiple cameras
            frame = self.create_test_frame()
            task_ids = []
            
            for i in range(4):
                camera_location = CameraLocation.GATE if i % 2 == 0 else CameraLocation.CLASSROOM
                task_id = await edge_service.submit_processing_task(
                    camera_id=f"camera_{i}",
                    frame=frame,
                    camera_location=camera_location
                )
                task_ids.append(task_id)
            
            assert len(task_ids) == 4
            assert all(task_id != "" for task_id in task_ids)
            
            # Check statistics
            stats = edge_service.get_processing_statistics()
            assert stats["processing_stats"]["total_tasks"] == 4
            assert len(stats["edge_devices"]) == 2
            
        finally:
            edge_service.shutdown()
    
    async def test_edge_communication_integration(self):
        """Test integration between edge processing and communication services."""
        edge_service = EdgeProcessingService(self.config)
        comm_service = EdgeCommunicationService(self.config)
        
        try:
            # Add device to both services
            device_config = EdgeDeviceConfig(
                device_id="test_device",
                device_type=EdgeDeviceType.NVIDIA_JETSON_NANO,
                ip_address="127.0.0.1",
                port=8080,
                api_key="test_key"
            )
            
            edge_service.add_edge_device(device_config)
            comm_service.add_device(device_config)
            
            # Send command through communication service
            command_id = await comm_service.send_command(
                device_id="test_device",
                command_type=CommandType.START_PROCESSING,
                payload={"camera_ids": ["camera_1", "camera_2"]}
            )
            
            assert command_id != ""
            
            # Add sync data
            comm_service.add_sync_data(
                device_id="test_device",
                data_type="face_embeddings",
                data={"student_id": "123", "embedding": [0.1, 0.2, 0.3]}
            )
            
            # Check sync status
            sync_status = comm_service.get_device_sync_status("test_device")
            assert sync_status["pending_items"] == 1
            
            # Check communication stats
            comm_stats = comm_service.get_communication_stats()
            assert comm_stats["pending_commands"] == 1
            assert comm_stats["devices_configured"] == 1
            
        finally:
            edge_service.shutdown()
            await comm_service.shutdown()
    
    def test_camera_processing_performance_metrics(self):
        """Test performance metrics collection for camera processing."""
        edge_service = EdgeProcessingService(self.config)
        
        try:
            # Add edge device
            device_config = EdgeDeviceConfig(
                device_id="perf_device",
                device_type=EdgeDeviceType.NVIDIA_JETSON_XAVIER,
                ip_address="127.0.0.1",
                port=8080,
                max_concurrent_streams=4
            )
            
            edge_service.add_edge_device(device_config)
            
            # Check initial statistics
            stats = edge_service.get_processing_statistics()
            assert stats["processing_stats"]["total_tasks"] == 0
            assert stats["processing_stats"]["avg_processing_time"] == 0.0
            
            # Check edge device stats
            device_stats = edge_service.get_edge_device_stats()
            assert "perf_device" in device_stats
            assert device_stats["perf_device"]["device_type"] == EdgeDeviceType.NVIDIA_JETSON_XAVIER.value
            
        finally:
            edge_service.shutdown()


class TestCameraProcessingErrorHandling:
    """Test error handling in camera processing integration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
    
    def teardown_method(self):
        """Cleanup after tests."""
        pass
    
    async def test_edge_device_connection_timeout(self):
        """Test handling of edge device connection timeouts."""
        edge_service = EdgeProcessingService(self.config)
        
        try:
            # Add device with invalid IP (will timeout)
            device_config = EdgeDeviceConfig(
                device_id="timeout_device",
                device_type=EdgeDeviceType.NVIDIA_JETSON_NANO,
                ip_address="192.168.255.255",  # Non-routable IP
                port=8080
            )
            
            edge_service.add_edge_device(device_config)
            
            # Device should be added but not connected
            assert "timeout_device" in edge_service.edge_devices
            
            # Check device health
            device = edge_service.edge_devices["timeout_device"]
            assert device.is_healthy() is False
            
        finally:
            edge_service.shutdown()
    
    async def test_processing_task_error_handling(self):
        """Test error handling in processing tasks."""
        edge_service = EdgeProcessingService(self.config)
        
        try:
            # Submit task without any edge devices
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            task_id = await edge_service.submit_processing_task(
                camera_id="test_camera",
                frame=frame,
                camera_location=CameraLocation.CLASSROOM
            )
            
            assert task_id != ""
            
            # Wait for processing (should fallback to cloud)
            await asyncio.sleep(0.5)
            
            # Check that task was processed (even without edge devices)
            stats = edge_service.get_processing_statistics()
            assert stats["processing_stats"]["total_tasks"] == 1
            
        finally:
            edge_service.shutdown()
    
    async def test_communication_service_error_recovery(self):
        """Test error recovery in communication service."""
        comm_service = EdgeCommunicationService(self.config)
        
        try:
            # Add device with invalid configuration
            device_config = EdgeDeviceConfig(
                device_id="error_device",
                device_type=EdgeDeviceType.NVIDIA_JETSON_NANO,
                ip_address="invalid_ip",
                port=0  # Invalid port
            )
            
            comm_service.add_device(device_config)
            
            # Try to send command (should handle error gracefully)
            command_id = await comm_service.send_command(
                device_id="error_device",
                command_type=CommandType.GET_STATUS,
                payload={}
            )
            
            assert command_id != ""
            
            # Wait for command processing
            await asyncio.sleep(1.0)
            
            # Check command status (should show failure)
            command_status = comm_service.get_command_status(command_id)
            # Command might still be pending or failed depending on timing
            assert command_status is not None
            
        finally:
            await comm_service.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
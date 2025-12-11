"""
Edge Processing Service for distributed face recognition and emotion analysis.

This service coordinates processing between edge devices (NVIDIA Jetson) and cloud services,
managing workload distribution and data synchronization.
"""

import asyncio
import aiohttp
import json
import numpy as np
import threading
import queue
import time
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
import logging
import base64
import cv2

from backend.core.base_service import BaseProcessingService
from backend.services.camera_config_manager import EdgeDeviceConfig, EdgeDeviceType
from backend.models.face_detection import FaceDetection, CameraLocation
from backend.models.emotion import EmotionResult


class EdgeProcessingMode(Enum):
    """Edge processing modes."""
    EDGE_ONLY = "edge_only"
    CLOUD_ONLY = "cloud_only"
    HYBRID = "hybrid"
    FAILOVER = "failover"


class ProcessingTask:
    """Processing task for edge devices."""
    
    def __init__(
        self,
        task_id: str,
        camera_id: str,
        frame: np.ndarray,
        timestamp: float,
        camera_location: CameraLocation,
        processing_type: str = "face_detection",
        priority: int = 1
    ):
        self.task_id = task_id
        self.camera_id = camera_id
        self.frame = frame
        self.timestamp = timestamp
        self.camera_location = camera_location
        self.processing_type = processing_type
        self.priority = priority
        self.created_at = time.time()
        self.assigned_device = None
        self.processing_started_at = None
        self.processing_completed_at = None
        self.results = None
        self.error = None


class EdgeDevice:
    """Edge device connection and management."""
    
    def __init__(self, config: EdgeDeviceConfig):
        self.config = config
        self.is_connected = False
        self.last_heartbeat = None
        self.current_load = 0
        self.processing_queue = queue.Queue()
        self.stats = {
            "tasks_processed": 0,
            "tasks_failed": 0,
            "avg_processing_time": 0.0,
            "last_task_time": None,
            "uptime_start": time.time()
        }
        self.logger = logging.getLogger(f"EdgeDevice_{config.device_id}")
    
    async def connect(self) -> bool:
        """Connect to edge device."""
        try:
            url = f"http://{self.config.ip_address}:{self.config.port}/health"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        self.is_connected = True
                        self.last_heartbeat = time.time()
                        self.logger.info(f"Connected to edge device {self.config.device_id}")
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to connect to edge device: {e}")
            self.is_connected = False
            return False
    
    async def send_heartbeat(self) -> bool:
        """Send heartbeat to edge device."""
        try:
            url = f"http://{self.config.ip_address}:{self.config.port}/heartbeat"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=5) as response:
                    if response.status == 200:
                        self.last_heartbeat = time.time()
                        return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Heartbeat failed: {e}")
            return False
    
    async def process_frame(self, task: ProcessingTask) -> Optional[dict]:
        """Send frame to edge device for processing."""
        try:
            # Encode frame to base64
            _, buffer = cv2.imencode('.jpg', task.frame)
            frame_b64 = base64.b64encode(buffer).decode('utf-8')
            
            # Prepare request data
            request_data = {
                "task_id": task.task_id,
                "camera_id": task.camera_id,
                "frame": frame_b64,
                "timestamp": task.timestamp,
                "camera_location": task.camera_location.value,
                "processing_type": task.processing_type
            }
            
            # Send to edge device
            url = f"http://{self.config.ip_address}:{self.config.port}/process"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=request_data,
                    timeout=30,
                    headers={"Authorization": f"Bearer {self.config.api_key}"} if self.config.api_key else {}
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        self.stats["tasks_processed"] += 1
                        self.stats["last_task_time"] = time.time()
                        return result
                    else:
                        self.logger.error(f"Edge processing failed with status {response.status}")
                        self.stats["tasks_failed"] += 1
                        return None
            
        except Exception as e:
            self.logger.error(f"Error processing frame on edge device: {e}")
            self.stats["tasks_failed"] += 1
            return None
    
    def get_load_score(self) -> float:
        """Get current load score (0.0 to 1.0)."""
        # Simple load calculation based on queue size and processing capabilities
        queue_load = min(self.processing_queue.qsize() / 10.0, 1.0)  # Normalize to max 10 tasks
        
        # Factor in device capabilities
        capability_factor = 1.0
        if self.config.device_type == EdgeDeviceType.NVIDIA_JETSON_NANO:
            capability_factor = 0.5  # Lower capability
        elif self.config.device_type == EdgeDeviceType.NVIDIA_JETSON_XAVIER:
            capability_factor = 0.8  # Higher capability
        elif self.config.device_type == EdgeDeviceType.NVIDIA_JETSON_ORIN:
            capability_factor = 1.0  # Highest capability
        
        return queue_load / capability_factor
    
    def is_healthy(self) -> bool:
        """Check if edge device is healthy."""
        if not self.is_connected:
            return False
        
        # Check last heartbeat
        if self.last_heartbeat:
            time_since_heartbeat = time.time() - self.last_heartbeat
            return time_since_heartbeat < 60  # 1 minute timeout
        
        return False
    
    def get_stats(self) -> dict:
        """Get edge device statistics."""
        uptime = time.time() - self.stats["uptime_start"]
        
        return {
            "device_id": self.config.device_id,
            "device_type": self.config.device_type.value,
            "is_connected": self.is_connected,
            "is_healthy": self.is_healthy(),
            "current_load": self.get_load_score(),
            "queue_size": self.processing_queue.qsize(),
            "tasks_processed": self.stats["tasks_processed"],
            "tasks_failed": self.stats["tasks_failed"],
            "success_rate": self.stats["tasks_processed"] / max(self.stats["tasks_processed"] + self.stats["tasks_failed"], 1),
            "uptime_seconds": uptime,
            "last_heartbeat": self.last_heartbeat
        }


class EdgeProcessingService(BaseProcessingService):
    """Service for managing edge processing and cloud coordination."""
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Edge devices
        self.edge_devices: Dict[str, EdgeDevice] = {}
        self.processing_mode = EdgeProcessingMode.HYBRID
        
        # Task management
        self.pending_tasks = queue.PriorityQueue()
        self.active_tasks: Dict[str, ProcessingTask] = {}
        self.completed_tasks: Dict[str, ProcessingTask] = {}
        
        # Processing threads
        self.processing_threads = []
        self.num_processing_threads = 2
        self.stop_event = threading.Event()
        
        # Load balancing
        self.load_balancer = EdgeLoadBalancer()
        
        # Statistics
        self.processing_stats = {
            "total_tasks": 0,
            "edge_processed": 0,
            "cloud_processed": 0,
            "failed_tasks": 0,
            "avg_processing_time": 0.0,
            "edge_utilization": 0.0
        }
        
        # Start processing
        self._start_processing_threads()
        self._start_heartbeat_monitor()
    
    def add_edge_device(self, device_config: EdgeDeviceConfig) -> bool:
        """Add edge device to the system."""
        try:
            if device_config.device_id in self.edge_devices:
                self.logger.warning(f"Edge device {device_config.device_id} already exists")
                return False
            
            edge_device = EdgeDevice(device_config)
            self.edge_devices[device_config.device_id] = edge_device
            
            # Attempt connection
            asyncio.create_task(edge_device.connect())
            
            self.logger.info(f"Added edge device: {device_config.device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add edge device: {e}")
            return False
    
    def remove_edge_device(self, device_id: str) -> bool:
        """Remove edge device from the system."""
        try:
            if device_id not in self.edge_devices:
                self.logger.warning(f"Edge device {device_id} not found")
                return False
            
            del self.edge_devices[device_id]
            self.logger.info(f"Removed edge device: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove edge device: {e}")
            return False
    
    async def submit_processing_task(
        self,
        camera_id: str,
        frame: np.ndarray,
        camera_location: CameraLocation,
        processing_type: str = "face_detection"
    ) -> str:
        """Submit frame for processing."""
        try:
            # Create task
            task_id = f"{camera_id}_{int(time.time() * 1000)}"
            task = ProcessingTask(
                task_id=task_id,
                camera_id=camera_id,
                frame=frame,
                timestamp=time.time(),
                camera_location=camera_location,
                processing_type=processing_type
            )
            
            # Add to pending queue
            priority = 1 if camera_location == CameraLocation.GATE else 2
            self.pending_tasks.put((priority, task))
            
            self.processing_stats["total_tasks"] += 1
            self.logger.debug(f"Submitted processing task: {task_id}")
            
            return task_id
            
        except Exception as e:
            self.logger.error(f"Failed to submit processing task: {e}")
            return ""
    
    def get_task_result(self, task_id: str) -> Optional[dict]:
        """Get processing task result."""
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return {
                "task_id": task_id,
                "status": "completed",
                "results": task.results,
                "processing_time": task.processing_completed_at - task.processing_started_at if task.processing_completed_at else None,
                "processed_on": task.assigned_device,
                "error": task.error
            }
        elif task_id in self.active_tasks:
            return {
                "task_id": task_id,
                "status": "processing",
                "assigned_device": self.active_tasks[task_id].assigned_device
            }
        else:
            return {
                "task_id": task_id,
                "status": "not_found"
            }
    
    def _start_processing_threads(self):
        """Start processing worker threads."""
        self.stop_event.clear()
        
        for i in range(self.num_processing_threads):
            thread = threading.Thread(
                target=self._processing_worker,
                name=f"EdgeProcessingWorker-{i}",
                daemon=True
            )
            thread.start()
            self.processing_threads.append(thread)
        
        self.logger.info(f"Started {self.num_processing_threads} edge processing threads")
    
    def _processing_worker(self):
        """Worker thread for processing tasks."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while not self.stop_event.is_set():
            try:
                # Get task from queue
                try:
                    priority, task = self.pending_tasks.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process the task
                loop.run_until_complete(self._process_task(task))
                
                # Mark task as done
                self.pending_tasks.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in edge processing worker: {e}")
                time.sleep(0.1)
        
        loop.close()
    
    async def _process_task(self, task: ProcessingTask):
        """Process individual task."""
        try:
            task.processing_started_at = time.time()
            self.active_tasks[task.task_id] = task
            
            # Determine processing strategy
            processing_strategy = self._determine_processing_strategy(task)
            
            if processing_strategy == "edge":
                # Process on edge device
                edge_device = self.load_balancer.select_best_device(
                    list(self.edge_devices.values()),
                    task.processing_type
                )
                
                if edge_device and edge_device.is_healthy():
                    task.assigned_device = edge_device.config.device_id
                    result = await edge_device.process_frame(task)
                    
                    if result:
                        task.results = result
                        self.processing_stats["edge_processed"] += 1
                    else:
                        # Fallback to cloud processing
                        await self._process_on_cloud(task)
                        self.processing_stats["cloud_processed"] += 1
                else:
                    # No healthy edge device, process on cloud
                    await self._process_on_cloud(task)
                    self.processing_stats["cloud_processed"] += 1
            
            else:
                # Process on cloud
                await self._process_on_cloud(task)
                self.processing_stats["cloud_processed"] += 1
            
            # Complete task
            task.processing_completed_at = time.time()
            
            # Move to completed tasks
            self.completed_tasks[task.task_id] = task
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            
            # Update statistics
            processing_time = task.processing_completed_at - task.processing_started_at
            total_processed = self.processing_stats["edge_processed"] + self.processing_stats["cloud_processed"]
            current_avg = self.processing_stats["avg_processing_time"]
            new_avg = (current_avg * (total_processed - 1) + processing_time) / total_processed
            self.processing_stats["avg_processing_time"] = new_avg
            
            self.logger.debug(f"Completed task {task.task_id} in {processing_time:.3f}s")
            
        except Exception as e:
            self.logger.error(f"Error processing task {task.task_id}: {e}")
            task.error = str(e)
            self.processing_stats["failed_tasks"] += 1
            
            # Move to completed tasks even if failed
            self.completed_tasks[task.task_id] = task
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
    
    def _determine_processing_strategy(self, task: ProcessingTask) -> str:
        """Determine whether to process on edge or cloud."""
        if self.processing_mode == EdgeProcessingMode.CLOUD_ONLY:
            return "cloud"
        elif self.processing_mode == EdgeProcessingMode.EDGE_ONLY:
            return "edge"
        elif self.processing_mode == EdgeProcessingMode.HYBRID:
            # Use edge for gate cameras (higher priority), cloud for classroom
            if task.camera_location == CameraLocation.GATE:
                return "edge"
            else:
                # Check edge device availability
                healthy_devices = [d for d in self.edge_devices.values() if d.is_healthy()]
                if healthy_devices and min(d.get_load_score() for d in healthy_devices) < 0.8:
                    return "edge"
                else:
                    return "cloud"
        else:  # FAILOVER
            # Try edge first, fallback to cloud
            return "edge"
    
    async def _process_on_cloud(self, task: ProcessingTask):
        """Process task on cloud services."""
        try:
            # Import cloud services
            from backend.services.face_recognition_service import FaceRecognitionService
            from backend.services.emotion_analysis_service import EmotionAnalysisService
            
            # Initialize services if not already done
            if not hasattr(self, 'cloud_face_service'):
                self.cloud_face_service = FaceRecognitionService(self.config)
            if not hasattr(self, 'cloud_emotion_service'):
                self.cloud_emotion_service = EmotionAnalysisService(self.config)
            
            results = {}
            
            if task.processing_type in ["face_detection", "all"]:
                # Face detection
                face_detections = self.cloud_face_service.detect_faces(
                    task.frame,
                    task.camera_location
                )
                results["face_detections"] = [
                    {
                        "bounding_box": detection.bounding_box,
                        "confidence": detection.confidence,
                        "liveness_score": detection.liveness_score,
                        "timestamp": detection.timestamp.isoformat()
                    }
                    for detection in face_detections
                ]
            
            if task.processing_type in ["emotion_analysis", "all"] and task.camera_location == CameraLocation.CLASSROOM:
                # Emotion analysis for classroom cameras
                emotion_results = []
                if "face_detections" in results:
                    for face_data in results["face_detections"]:
                        # Extract face ROI
                        x, y, w, h = face_data["bounding_box"]
                        face_roi = task.frame[y:y+h, x:x+w]
                        
                        if face_roi.size > 0:
                            emotion_result = self.cloud_emotion_service.analyze_emotion(face_roi)
                            emotion_results.append({
                                "emotion": emotion_result.emotion.value,
                                "confidence": emotion_result.confidence,
                                "engagement_score": emotion_result.engagement_score,
                                "timestamp": emotion_result.timestamp.isoformat()
                            })
                
                results["emotion_results"] = emotion_results
            
            task.results = results
            task.assigned_device = "cloud"
            
        except Exception as e:
            self.logger.error(f"Cloud processing failed: {e}")
            task.error = str(e)
    
    def _start_heartbeat_monitor(self):
        """Start heartbeat monitoring for edge devices."""
        heartbeat_thread = threading.Thread(
            target=self._heartbeat_monitor,
            name="EdgeHeartbeatMonitor",
            daemon=True
        )
        heartbeat_thread.start()
        self.logger.info("Started edge device heartbeat monitor")
    
    def _heartbeat_monitor(self):
        """Monitor edge device health with heartbeats."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while not self.stop_event.is_set():
            try:
                # Send heartbeats to all devices
                for device in self.edge_devices.values():
                    if device.is_connected:
                        loop.run_until_complete(device.send_heartbeat())
                
                # Calculate edge utilization
                if self.edge_devices:
                    total_load = sum(device.get_load_score() for device in self.edge_devices.values())
                    self.processing_stats["edge_utilization"] = total_load / len(self.edge_devices)
                
                time.sleep(30)  # Heartbeat every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in heartbeat monitor: {e}")
                time.sleep(10)
        
        loop.close()
    
    def get_edge_device_stats(self) -> Dict[str, dict]:
        """Get statistics for all edge devices."""
        return {device_id: device.get_stats() for device_id, device in self.edge_devices.items()}
    
    def get_processing_statistics(self) -> dict:
        """Get comprehensive processing statistics."""
        return {
            "processing_stats": self.processing_stats.copy(),
            "edge_devices": self.get_edge_device_stats(),
            "active_tasks": len(self.active_tasks),
            "pending_tasks": self.pending_tasks.qsize(),
            "completed_tasks": len(self.completed_tasks),
            "processing_mode": self.processing_mode.value
        }
    
    def set_processing_mode(self, mode: EdgeProcessingMode):
        """Set processing mode."""
        self.processing_mode = mode
        self.logger.info(f"Processing mode set to: {mode.value}")
    
    def shutdown(self):
        """Shutdown edge processing service."""
        self.logger.info("Shutting down edge processing service")
        
        # Stop processing
        self.stop_event.set()
        
        # Wait for threads to finish
        for thread in self.processing_threads:
            if thread.is_alive():
                thread.join(timeout=5.0)
        
        self.logger.info("Edge processing service shutdown complete")


class EdgeLoadBalancer:
    """Load balancer for edge devices."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def select_best_device(
        self,
        devices: List[EdgeDevice],
        processing_type: str
    ) -> Optional[EdgeDevice]:
        """Select best edge device for processing."""
        try:
            # Filter healthy devices
            healthy_devices = [d for d in devices if d.is_healthy()]
            
            if not healthy_devices:
                return None
            
            # Filter devices that support the processing type
            capable_devices = []
            for device in healthy_devices:
                capabilities = device.config.processing_capabilities
                if processing_type == "face_detection" and capabilities.get("face_detection", False):
                    capable_devices.append(device)
                elif processing_type == "emotion_analysis" and capabilities.get("emotion_analysis", False):
                    capable_devices.append(device)
                elif processing_type == "all":
                    if capabilities.get("face_detection", False) and capabilities.get("emotion_analysis", False):
                        capable_devices.append(device)
            
            if not capable_devices:
                # Fallback to any healthy device
                capable_devices = healthy_devices
            
            # Select device with lowest load
            best_device = min(capable_devices, key=lambda d: d.get_load_score())
            
            self.logger.debug(f"Selected device {best_device.config.device_id} with load {best_device.get_load_score():.2f}")
            return best_device
            
        except Exception as e:
            self.logger.error(f"Error selecting best device: {e}")
            return None
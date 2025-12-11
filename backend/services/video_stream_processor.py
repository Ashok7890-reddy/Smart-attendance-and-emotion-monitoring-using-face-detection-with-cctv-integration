"""
Video Stream Processor for real-time face detection and processing.

This service coordinates video streams from multiple cameras with face recognition
and emotion analysis services, managing processing queues and frame coordination.
"""

import cv2
import numpy as np
import threading
import queue
import time
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime
from enum import Enum
import logging

from backend.core.base_service import BaseProcessingService
from backend.services.camera_service import CameraService
from backend.services.face_recognition_service import FaceRecognitionService
from backend.services.emotion_analysis_service import EmotionAnalysisService
from backend.models.face_detection import FaceDetection, CameraLocation
from backend.models.emotion import EmotionResult


class ProcessingPriority(Enum):
    """Processing priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class FrameProcessingTask:
    """Individual frame processing task."""
    
    def __init__(
        self,
        camera_id: str,
        frame: np.ndarray,
        timestamp: float,
        camera_location: CameraLocation,
        priority: ProcessingPriority = ProcessingPriority.NORMAL,
        callback: Optional[Callable] = None
    ):
        self.camera_id = camera_id
        self.frame = frame
        self.timestamp = timestamp
        self.camera_location = camera_location
        self.priority = priority
        self.callback = callback
        self.created_at = time.time()
        self.processing_started_at = None
        self.processing_completed_at = None
        self.results = {}


class VideoStreamProcessor(BaseProcessingService):
    """Video stream processor for coordinated face detection and analysis."""
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Initialize services
        self.camera_service = CameraService(config)
        self.face_recognition_service = FaceRecognitionService(config)
        self.emotion_analysis_service = EmotionAnalysisService(config)
        
        # Processing queues
        self.processing_queue = queue.PriorityQueue()
        self.result_queue = queue.Queue()
        
        # Processing threads
        self.processing_threads = []
        self.num_processing_threads = 4  # Configurable based on system resources
        self.stop_event = threading.Event()
        
        # Frame coordination
        self.frame_coordinators = {}
        self.processing_stats = {
            "frames_processed": 0,
            "faces_detected": 0,
            "emotions_analyzed": 0,
            "processing_time_avg": 0.0,
            "queue_size_max": 0,
            "dropped_frames": 0
        }
        
        # Callbacks for results
        self.result_callbacks = []
        
        # Start processing
        self._start_processing_threads()
        self._start_result_handler()
    
    def start_camera_processing(self, camera_id: str) -> bool:
        """Start processing frames from a specific camera."""
        try:
            # Start camera stream
            if not self.camera_service.start_stream(camera_id):
                self.logger.error(f"Failed to start camera stream: {camera_id}")
                return False
            
            # Add frame processor
            self.camera_service.add_frame_processor(
                camera_id,
                lambda frame: self._queue_frame_for_processing(camera_id, frame)
            )
            
            # Create frame coordinator
            self.frame_coordinators[camera_id] = FrameCoordinator(camera_id)
            
            self.logger.info(f"Started processing for camera: {camera_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start camera processing for {camera_id}: {e}")
            return False
    
    def stop_camera_processing(self, camera_id: str) -> bool:
        """Stop processing frames from a specific camera."""
        try:
            # Stop camera stream
            self.camera_service.stop_stream(camera_id)
            
            # Remove frame coordinator
            if camera_id in self.frame_coordinators:
                del self.frame_coordinators[camera_id]
            
            self.logger.info(f"Stopped processing for camera: {camera_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to stop camera processing for {camera_id}: {e}")
            return False
    
    def start_all_camera_processing(self) -> bool:
        """Start processing for all configured cameras."""
        success_count = 0
        camera_stats = self.camera_service.get_all_camera_stats()
        
        for camera_id in camera_stats.keys():
            if self.start_camera_processing(camera_id):
                success_count += 1
        
        total_cameras = len(camera_stats)
        self.logger.info(f"Started processing for {success_count}/{total_cameras} cameras")
        
        return success_count == total_cameras
    
    def stop_all_camera_processing(self):
        """Stop processing for all cameras."""
        camera_stats = self.camera_service.get_all_camera_stats()
        
        for camera_id in camera_stats.keys():
            self.stop_camera_processing(camera_id)
        
        self.logger.info("Stopped processing for all cameras")
    
    def _queue_frame_for_processing(self, camera_id: str, frame: np.ndarray):
        """Queue frame for processing."""
        try:
            # Get camera location
            camera_stats = self.camera_service.get_camera_stats(camera_id)
            if not camera_stats:
                return
            
            location_str = camera_stats.get("location", "classroom")
            camera_location = CameraLocation.GATE if location_str == "gate" else CameraLocation.CLASSROOM
            
            # Determine priority based on camera location
            priority = ProcessingPriority.HIGH if camera_location == CameraLocation.GATE else ProcessingPriority.NORMAL
            
            # Create processing task
            task = FrameProcessingTask(
                camera_id=camera_id,
                frame=frame.copy(),
                timestamp=time.time(),
                camera_location=camera_location,
                priority=priority
            )
            
            # Add to queue with priority
            try:
                self.processing_queue.put_nowait((priority.value, task))
                
                # Update queue size statistics
                current_queue_size = self.processing_queue.qsize()
                if current_queue_size > self.processing_stats["queue_size_max"]:
                    self.processing_stats["queue_size_max"] = current_queue_size
                    
            except queue.Full:
                self.processing_stats["dropped_frames"] += 1
                self.logger.warning(f"Processing queue full, dropped frame from {camera_id}")
            
        except Exception as e:
            self.logger.error(f"Error queuing frame for processing: {e}")
    
    def _start_processing_threads(self):
        """Start processing worker threads."""
        self.stop_event.clear()
        
        for i in range(self.num_processing_threads):
            thread = threading.Thread(
                target=self._processing_worker,
                name=f"ProcessingWorker-{i}",
                daemon=True
            )
            thread.start()
            self.processing_threads.append(thread)
        
        self.logger.info(f"Started {self.num_processing_threads} processing threads")
    
    def _processing_worker(self):
        """Worker thread for processing frames."""
        while not self.stop_event.is_set():
            try:
                # Get task from queue with timeout
                try:
                    priority, task = self.processing_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process the frame
                self._process_frame_task(task)
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in processing worker: {e}")
                time.sleep(0.1)
    
    def _process_frame_task(self, task: FrameProcessingTask):
        """Process individual frame task."""
        try:
            task.processing_started_at = time.time()
            
            # Face detection
            face_detections = self.face_recognition_service.detect_faces(
                task.frame,
                task.camera_location
            )
            
            task.results["face_detections"] = face_detections
            self.processing_stats["faces_detected"] += len(face_detections)
            
            # Emotion analysis for classroom cameras
            emotion_results = []
            if task.camera_location == CameraLocation.CLASSROOM:
                for detection in face_detections:
                    # Extract face ROI for emotion analysis
                    face_roi = self._extract_face_roi(task.frame, detection.bounding_box)
                    if face_roi is not None:
                        emotion_result = self.emotion_analysis_service.analyze_emotion(face_roi)
                        emotion_results.append(emotion_result)
                
                task.results["emotion_results"] = emotion_results
                self.processing_stats["emotions_analyzed"] += len(emotion_results)
            
            # Update processing statistics
            task.processing_completed_at = time.time()
            processing_time = task.processing_completed_at - task.processing_started_at
            
            # Update average processing time
            total_processed = self.processing_stats["frames_processed"]
            current_avg = self.processing_stats["processing_time_avg"]
            new_avg = (current_avg * total_processed + processing_time) / (total_processed + 1)
            self.processing_stats["processing_time_avg"] = new_avg
            self.processing_stats["frames_processed"] += 1
            
            # Add to result queue
            self.result_queue.put(task)
            
            # Execute callback if provided
            if task.callback:
                task.callback(task)
            
            self.logger.debug(
                f"Processed frame from {task.camera_id}: "
                f"{len(face_detections)} faces, {len(emotion_results)} emotions, "
                f"{processing_time:.3f}s"
            )
            
        except Exception as e:
            self.logger.error(f"Error processing frame task: {e}")
    
    def _extract_face_roi(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """Extract face region of interest from frame."""
        try:
            x, y, w, h = bbox
            
            # Validate bounding box
            if x < 0 or y < 0 or x + w > frame.shape[1] or y + h > frame.shape[0]:
                return None
            
            # Extract face ROI
            face_roi = frame[y:y+h, x:x+w]
            
            if face_roi.size == 0:
                return None
            
            return face_roi
            
        except Exception as e:
            self.logger.error(f"Error extracting face ROI: {e}")
            return None
    
    def _start_result_handler(self):
        """Start result handler thread."""
        result_thread = threading.Thread(
            target=self._result_handler,
            name="ResultHandler",
            daemon=True
        )
        result_thread.start()
        self.logger.info("Started result handler thread")
    
    def _result_handler(self):
        """Handle processing results."""
        while not self.stop_event.is_set():
            try:
                # Get result from queue with timeout
                try:
                    task = self.result_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Process results through callbacks
                for callback in self.result_callbacks:
                    try:
                        callback(task)
                    except Exception as e:
                        self.logger.error(f"Error in result callback: {e}")
                
                # Mark result as processed
                self.result_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error in result handler: {e}")
                time.sleep(0.1)
    
    def add_result_callback(self, callback: Callable[[FrameProcessingTask], None]):
        """Add callback for processing results."""
        self.result_callbacks.append(callback)
        self.logger.info("Added result callback")
    
    def remove_result_callback(self, callback: Callable[[FrameProcessingTask], None]):
        """Remove result callback."""
        try:
            self.result_callbacks.remove(callback)
            self.logger.info("Removed result callback")
        except ValueError:
            self.logger.warning("Result callback not found")
    
    def get_processing_statistics(self) -> dict:
        """Get comprehensive processing statistics."""
        camera_stats = self.camera_service.get_all_camera_stats()
        
        return {
            "video_processing": self.processing_stats.copy(),
            "camera_stats": camera_stats,
            "queue_size": self.processing_queue.qsize(),
            "result_queue_size": self.result_queue.qsize(),
            "active_threads": len([t for t in self.processing_threads if t.is_alive()]),
            "face_recognition_stats": self.face_recognition_service.get_recognition_stats(),
            "emotion_analysis_stats": self.emotion_analysis_service.get_processing_stats()
        }
    
    def get_camera_frame(self, camera_id: str) -> Optional[np.ndarray]:
        """Get current frame from specific camera."""
        return self.camera_service.get_frame(camera_id)
    
    def get_all_camera_frames(self) -> Dict[str, Optional[np.ndarray]]:
        """Get current frames from all cameras."""
        frames = {}
        camera_stats = self.camera_service.get_all_camera_stats()
        
        for camera_id in camera_stats.keys():
            frames[camera_id] = self.camera_service.get_frame(camera_id)
        
        return frames
    
    def shutdown(self):
        """Shutdown video stream processor."""
        self.logger.info("Shutting down video stream processor")
        
        # Stop processing
        self.stop_event.set()
        
        # Stop camera processing
        self.stop_all_camera_processing()
        
        # Wait for processing threads to finish
        for thread in self.processing_threads:
            if thread.is_alive():
                thread.join(timeout=5.0)
        
        # Shutdown camera service
        self.camera_service.shutdown()
        
        self.logger.info("Video stream processor shutdown complete")
    
    def health_check(self) -> dict:
        """Extended health check for video stream processor."""
        base_health = super().health_check()
        
        # Check processing threads
        active_threads = len([t for t in self.processing_threads if t.is_alive()])
        threads_healthy = active_threads == self.num_processing_threads
        
        # Check queue sizes
        processing_queue_size = self.processing_queue.qsize()
        result_queue_size = self.result_queue.qsize()
        queues_healthy = processing_queue_size < 100 and result_queue_size < 50
        
        # Get camera health
        camera_health = self.camera_service.health_check()
        
        base_health.update({
            "processing_threads": {
                "active": active_threads,
                "expected": self.num_processing_threads,
                "healthy": threads_healthy
            },
            "queues": {
                "processing_queue_size": processing_queue_size,
                "result_queue_size": result_queue_size,
                "healthy": queues_healthy
            },
            "camera_service": camera_health,
            "overall_healthy": threads_healthy and queues_healthy and camera_health.get("overall_camera_health", False)
        })
        
        return base_health


class FrameCoordinator:
    """Coordinates frame processing for individual cameras."""
    
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.frame_history = []
        self.max_history = 30  # Keep last 30 frames for analysis
        self.lock = threading.Lock()
        self.logger = logging.getLogger(f"FrameCoordinator_{camera_id}")
    
    def add_frame_result(self, task: FrameProcessingTask):
        """Add processed frame result to history."""
        with self.lock:
            self.frame_history.append({
                "timestamp": task.timestamp,
                "processing_time": task.processing_completed_at - task.processing_started_at,
                "face_count": len(task.results.get("face_detections", [])),
                "emotion_count": len(task.results.get("emotion_results", [])),
                "results": task.results
            })
            
            # Maintain history size
            if len(self.frame_history) > self.max_history:
                self.frame_history.pop(0)
    
    def get_recent_results(self, count: int = 10) -> List[dict]:
        """Get recent frame processing results."""
        with self.lock:
            return self.frame_history[-count:] if self.frame_history else []
    
    def get_statistics(self) -> dict:
        """Get frame processing statistics for this camera."""
        with self.lock:
            if not self.frame_history:
                return {"camera_id": self.camera_id, "no_data": True}
            
            recent_frames = self.frame_history[-10:]  # Last 10 frames
            
            avg_processing_time = sum(f["processing_time"] for f in recent_frames) / len(recent_frames)
            avg_face_count = sum(f["face_count"] for f in recent_frames) / len(recent_frames)
            avg_emotion_count = sum(f["emotion_count"] for f in recent_frames) / len(recent_frames)
            
            return {
                "camera_id": self.camera_id,
                "total_frames_processed": len(self.frame_history),
                "avg_processing_time": avg_processing_time,
                "avg_face_count": avg_face_count,
                "avg_emotion_count": avg_emotion_count,
                "last_frame_timestamp": self.frame_history[-1]["timestamp"]
            }
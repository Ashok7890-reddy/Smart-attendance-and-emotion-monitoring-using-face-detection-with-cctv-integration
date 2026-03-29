"""
DeepFace Emotion Analysis Service for the Smart Attendance System.

This service uses DeepFace library for advanced emotion recognition and analysis,
providing more accurate emotion detection than traditional CNN models.
"""

import cv2
import numpy as np
import base64
import io
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging
from PIL import Image
import asyncio
import concurrent.futures

try:
    from deepface import DeepFace
    from deepface.commons import functions
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    DeepFace = None
    functions = None

from backend.core.base_service import BaseProcessingService
from backend.core.interfaces import IEmotionAnalysisService
from backend.models.emotion import EmotionResult, EmotionStatistics, EmotionType
from backend.services.engagement_scoring import EngagementScoringAlgorithm, RealTimeEngagementTracker
from backend.services.websocket_integration_service import get_websocket_integration


class DeepFaceEmotionService(BaseProcessingService, IEmotionAnalysisService):
    """Advanced emotion analysis service using DeepFace library."""
    
    def __init__(self, config=None):
        super().__init__(config)
        
        if not DEEPFACE_AVAILABLE:
            raise ImportError("DeepFace library is not available. Install with: pip install deepface")
        
        # DeepFace configuration — Facenet512 + retinaface for best accuracy
        self.face_recognition_model = "Facenet512"  # 512D embeddings, highest accuracy
        self.detector_backend = "retinaface"         # Best face detector available
        self.emotion_model = "Emotion"               # DeepFace built-in emotion model
        self.confidence_threshold = 0.7
        
        # Emotion mapping from DeepFace to our engagement categories
        self.emotion_to_engagement = {
            'happy': EmotionType.INTERESTED,
            'surprise': EmotionType.INTERESTED,
            'neutral': EmotionType.BORED,
            'sad': EmotionType.SLEEPY,
            'angry': EmotionType.CONFUSED,
            'disgust': EmotionType.BORED,
            'fear': EmotionType.CONFUSED
        }
        
        # Engagement scoring weights
        self.engagement_weights = {
            'happy': 0.95,
            'surprise': 0.85,
            'neutral': 0.50,
            'sad': 0.20,
            'angry': 0.30,
            'disgust': 0.15,
            'fear': 0.25
        }
        
        self.session_statistics = {}
        self.websocket_integration = get_websocket_integration()
        
        # Initialize engagement scoring components
        self.engagement_algorithm = EngagementScoringAlgorithm()
        self.real_time_tracker = RealTimeEngagementTracker()
        
        # Thread pool for async processing
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        
        self._initialize_deepface()
    
    def _initialize_deepface(self):
        """Initialize DeepFace models and verify functionality."""
        try:
            self.logger.info("Initializing DeepFace emotion analysis...")
            
            # Create a test image to warm up the models
            test_image = np.zeros((224, 224, 3), dtype=np.uint8)
            test_image.fill(128)  # Gray image
            
            # Test emotion analysis
            try:
                result = DeepFace.analyze(
                    img_path=test_image,
                    actions=['emotion'],
                    detector_backend=self.detector_backend,
                    enforce_detection=False,
                    silent=True
                )
                self.logger.info("✅ DeepFace emotion analysis initialized successfully")
                self.logger.info(f"Using detector: {self.detector_backend}, model: {self.emotion_model}")
                
            except Exception as e:
                self.logger.warning(f"DeepFace initialization test failed: {e}")
                # Try with different backend
                self.detector_backend = "ssd"
                self.logger.info(f"Switching to {self.detector_backend} detector backend")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize DeepFace: {e}")
            raise
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for DeepFace analysis."""
        try:
            # Ensure image is in correct format
            if len(image.shape) == 3 and image.shape[2] == 3:
                # BGR to RGB conversion for DeepFace
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            elif len(image.shape) == 2:
                # Grayscale to RGB
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            
            # Resize if too small (DeepFace works better with larger images)
            height, width = image.shape[:2]
            if height < 224 or width < 224:
                scale = max(224 / height, 224 / width)
                new_height, new_width = int(height * scale), int(width * scale)
                image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            
            return image
            
        except Exception as e:
            self.logger.error(f"Image preprocessing failed: {e}")
            raise
    
    def _analyze_emotion_sync(self, image: np.ndarray) -> Dict[str, Any]:
        """Synchronous emotion analysis using DeepFace."""
        try:
            # Preprocess image
            processed_image = self._preprocess_image(image)
            
            # Analyze emotions using DeepFace
            result = DeepFace.analyze(
                img_path=processed_image,
                actions=['emotion'],
                detector_backend=self.detector_backend,
                enforce_detection=False,  # Don't fail if no face detected
                silent=True
            )
            
            # Handle both single face and multiple faces results
            if isinstance(result, list):
                # Multiple faces detected, use the first one
                if len(result) > 0:
                    emotion_data = result[0]['emotion']
                else:
                    raise ValueError("No faces detected in image")
            else:
                # Single face result
                emotion_data = result['emotion']
            
            return emotion_data
            
        except Exception as e:
            self.logger.error(f"DeepFace emotion analysis failed: {e}")
            # Return neutral emotion as fallback
            return {
                'angry': 0.0,
                'disgust': 0.0,
                'fear': 0.0,
                'happy': 0.0,
                'sad': 0.0,
                'surprise': 0.0,
                'neutral': 1.0
            }
    
    async def analyze_emotion_async(self, image: np.ndarray, student_id: str = "unknown") -> EmotionResult:
        """Asynchronous emotion analysis."""
        loop = asyncio.get_event_loop()
        
        try:
            # Run DeepFace analysis in thread pool
            emotion_data = await loop.run_in_executor(
                self.executor, 
                self._analyze_emotion_sync, 
                image
            )
            
            # Process results
            return self._process_emotion_results(emotion_data, student_id)
            
        except Exception as e:
            self.logger.error(f"Async emotion analysis failed: {e}")
            return self._create_fallback_result(student_id)
    
    def analyze_emotion(self, face_roi: np.ndarray, student_id: str = "unknown") -> EmotionResult:
        """Analyze emotion from face region of interest (synchronous)."""
        try:
            # Validate input
            if face_roi is None or face_roi.size == 0:
                raise ValueError("Invalid face ROI provided")
            
            # Analyze emotions
            emotion_data = self._analyze_emotion_sync(face_roi)
            
            # Process results
            result = self._process_emotion_results(emotion_data, student_id)
            
            # Update processing stats
            self._update_stats(success=result.confidence >= self.confidence_threshold)
            
            self.logger.debug(f"Emotion analysis completed: {result.emotion.value} (confidence: {result.confidence:.2f})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Emotion analysis failed: {e}")
            self._update_stats(success=False)
            return self._create_fallback_result(student_id)
    
    def _process_emotion_results(self, emotion_data: Dict[str, float], student_id: str) -> EmotionResult:
        """Process DeepFace emotion results into our format."""
        try:
            # Find dominant emotion
            dominant_emotion = max(emotion_data, key=emotion_data.get)
            confidence = emotion_data[dominant_emotion] / 100.0  # DeepFace returns percentages
            
            # Map to our engagement categories
            engagement_type = self.emotion_to_engagement.get(dominant_emotion, EmotionType.BORED)
            
            # Calculate engagement score
            engagement_score = self._calculate_engagement_score(emotion_data)
            
            # Create detailed emotion breakdown
            emotion_breakdown = {
                'raw_emotions': emotion_data,
                'dominant_emotion': dominant_emotion,
                'engagement_distribution': self._calculate_engagement_distribution(emotion_data)
            }
            
            result = EmotionResult(
                student_id=student_id,
                emotion=engagement_type,
                confidence=confidence,
                timestamp=datetime.now(),
                engagement_score=engagement_score,
                raw_emotion=dominant_emotion,
                emotion_breakdown=emotion_breakdown
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing emotion results: {e}")
            return self._create_fallback_result(student_id)
    
    def _calculate_engagement_score(self, emotion_data: Dict[str, float]) -> float:
        """Calculate engagement score from emotion probabilities."""
        try:
            total_score = 0.0
            total_weight = 0.0
            
            for emotion, probability in emotion_data.items():
                weight = self.engagement_weights.get(emotion, 0.5)
                normalized_prob = probability / 100.0  # Convert percentage to probability
                total_score += weight * normalized_prob
                total_weight += normalized_prob
            
            if total_weight > 0:
                engagement_score = total_score / total_weight
            else:
                engagement_score = 0.5  # Neutral engagement
            
            return max(0.0, min(1.0, engagement_score))
            
        except Exception as e:
            self.logger.error(f"Engagement score calculation failed: {e}")
            return 0.5
    
    def _calculate_engagement_distribution(self, emotion_data: Dict[str, float]) -> Dict[str, float]:
        """Calculate engagement level distribution."""
        try:
            engagement_dist = {
                'interested': 0.0,
                'bored': 0.0,
                'confused': 0.0,
                'sleepy': 0.0
            }
            
            # Map emotions to engagement levels
            emotion_to_engagement_str = {
                'happy': 'interested',
                'surprise': 'interested',
                'neutral': 'bored',
                'sad': 'sleepy',
                'angry': 'confused',
                'disgust': 'bored',
                'fear': 'confused'
            }
            
            for emotion, probability in emotion_data.items():
                engagement_level = emotion_to_engagement_str.get(emotion, 'bored')
                engagement_dist[engagement_level] += probability / 100.0
            
            return engagement_dist
            
        except Exception as e:
            self.logger.error(f"Engagement distribution calculation failed: {e}")
            return {'interested': 0.25, 'bored': 0.25, 'confused': 0.25, 'sleepy': 0.25}
    
    def _create_fallback_result(self, student_id: str) -> EmotionResult:
        """Create fallback result when analysis fails."""
        return EmotionResult(
            student_id=student_id,
            emotion=EmotionType.BORED,
            confidence=0.0,
            timestamp=datetime.now(),
            engagement_score=0.5,
            raw_emotion='neutral',
            emotion_breakdown={
                'raw_emotions': {'neutral': 100.0},
                'dominant_emotion': 'neutral',
                'engagement_distribution': {'interested': 0.0, 'bored': 1.0, 'confused': 0.0, 'sleepy': 0.0}
            }
        )
    
    def analyze_batch_emotions(self, images: List[np.ndarray], student_ids: List[str] = None) -> List[EmotionResult]:
        """Analyze emotions for multiple images in batch."""
        if student_ids is None:
            student_ids = [f"student_{i}" for i in range(len(images))]
        
        results = []
        for i, image in enumerate(images):
            student_id = student_ids[i] if i < len(student_ids) else f"student_{i}"
            result = self.analyze_emotion(image, student_id)
            results.append(result)
        
        return results
    
    async def analyze_batch_emotions_async(self, images: List[np.ndarray], student_ids: List[str] = None) -> List[EmotionResult]:
        """Analyze emotions for multiple images asynchronously."""
        if student_ids is None:
            student_ids = [f"student_{i}" for i in range(len(images))]
        
        tasks = []
        for i, image in enumerate(images):
            student_id = student_ids[i] if i < len(student_ids) else f"student_{i}"
            task = self.analyze_emotion_async(image, student_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Batch emotion analysis failed for image {i}: {result}")
                processed_results.append(self._create_fallback_result(student_ids[i]))
            else:
                processed_results.append(result)
        
        return processed_results
    
    def analyze_emotion_from_base64(self, base64_image: str, student_id: str = "unknown") -> EmotionResult:
        """Analyze emotion from base64 encoded image."""
        try:
            # Decode base64 image
            image_data = base64.b64decode(base64_image)
            image = Image.open(io.BytesIO(image_data))
            image_np = np.array(image)
            
            # Convert RGB to BGR for OpenCV
            if len(image_np.shape) == 3 and image_np.shape[2] == 3:
                image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
            
            return self.analyze_emotion(image_np, student_id)
            
        except Exception as e:
            self.logger.error(f"Base64 emotion analysis failed: {e}")
            return self._create_fallback_result(student_id)
    
    def get_emotion_statistics_summary(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive emotion statistics for a session."""
        try:
            stats = self.get_session_statistics(session_id)
            
            if stats.total_frames == 0:
                return {"error": "No emotion data available for session"}
            
            # Calculate advanced metrics
            emotion_timeline = stats.emotion_timeline
            
            # Engagement trends
            engagement_scores = [result.engagement_score for result in emotion_timeline]
            engagement_trend = self._calculate_trend(engagement_scores)
            
            # Emotion stability (how consistent emotions are)
            emotion_stability = self._calculate_emotion_stability(emotion_timeline)
            
            # Peak engagement periods
            peak_periods = self._identify_peak_engagement_periods(emotion_timeline)
            
            summary = {
                "session_id": session_id,
                "total_frames": stats.total_frames,
                "average_engagement": stats.average_engagement_score,
                "emotion_distribution": stats.emotion_percentages,
                "engagement_trend": engagement_trend,
                "emotion_stability": emotion_stability,
                "peak_engagement_periods": peak_periods,
                "dominant_emotion": max(stats.emotion_counts, key=stats.emotion_counts.get).value,
                "analysis_quality": self._assess_analysis_quality(emotion_timeline)
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Failed to generate emotion statistics summary: {e}")
            return {"error": str(e)}
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a series of values."""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear trend calculation
        x = list(range(len(values)))
        n = len(values)
        
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        if slope > 0.01:
            return "increasing"
        elif slope < -0.01:
            return "decreasing"
        else:
            return "stable"
    
    def _calculate_emotion_stability(self, emotion_timeline: List[EmotionResult]) -> float:
        """Calculate how stable/consistent emotions are over time."""
        if len(emotion_timeline) < 2:
            return 1.0
        
        # Calculate variance in engagement scores
        engagement_scores = [result.engagement_score for result in emotion_timeline]
        mean_engagement = sum(engagement_scores) / len(engagement_scores)
        variance = sum((score - mean_engagement) ** 2 for score in engagement_scores) / len(engagement_scores)
        
        # Convert variance to stability score (lower variance = higher stability)
        stability = max(0.0, 1.0 - variance)
        return stability
    
    def _identify_peak_engagement_periods(self, emotion_timeline: List[EmotionResult]) -> List[Dict[str, Any]]:
        """Identify periods of peak engagement."""
        if len(emotion_timeline) < 3:
            return []
        
        peaks = []
        engagement_scores = [result.engagement_score for result in emotion_timeline]
        
        # Find local maxima above threshold
        threshold = 0.7
        for i in range(1, len(engagement_scores) - 1):
            if (engagement_scores[i] > engagement_scores[i-1] and 
                engagement_scores[i] > engagement_scores[i+1] and 
                engagement_scores[i] > threshold):
                
                peaks.append({
                    "timestamp": emotion_timeline[i].timestamp.isoformat(),
                    "engagement_score": engagement_scores[i],
                    "emotion": emotion_timeline[i].emotion.value,
                    "student_id": emotion_timeline[i].student_id
                })
        
        return peaks
    
    def _assess_analysis_quality(self, emotion_timeline: List[EmotionResult]) -> Dict[str, Any]:
        """Assess the quality of emotion analysis."""
        if not emotion_timeline:
            return {"quality": "no_data", "confidence": 0.0}
        
        # Calculate average confidence
        confidences = [result.confidence for result in emotion_timeline]
        avg_confidence = sum(confidences) / len(confidences)
        
        # Assess data completeness
        total_expected = len(emotion_timeline)  # Assuming we expect one result per frame
        completeness = len([r for r in emotion_timeline if r.confidence > 0.5]) / total_expected
        
        # Overall quality assessment
        if avg_confidence > 0.8 and completeness > 0.9:
            quality = "excellent"
        elif avg_confidence > 0.6 and completeness > 0.7:
            quality = "good"
        elif avg_confidence > 0.4 and completeness > 0.5:
            quality = "fair"
        else:
            quality = "poor"
        
        return {
            "quality": quality,
            "average_confidence": avg_confidence,
            "completeness": completeness,
            "total_samples": len(emotion_timeline)
        }
    
    def health_check(self) -> dict:
        """Health check for DeepFace emotion analysis service."""
        base_health = super().health_check()
        
        deepface_health = {
            "deepface_available": DEEPFACE_AVAILABLE,
            "detector_backend": self.detector_backend,
            "emotion_model": self.emotion_model,
            "confidence_threshold": self.confidence_threshold,
            "active_sessions": len(self.session_statistics),
            "processing_stats": self.get_processing_stats(),
            "thread_pool_active": not self.executor._shutdown
        }
        
        base_health.update(deepface_health)
        return base_health
    
    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)


# Create global instance
deepface_emotion_service = DeepFaceEmotionService()
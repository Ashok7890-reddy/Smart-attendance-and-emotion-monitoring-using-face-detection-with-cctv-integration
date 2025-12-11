"""
Emotion Analysis Service for the Smart Attendance System.

This service implements emotion classification for facial expressions,
focusing on three categories: Interested, Bored, and Confused.
"""

import cv2
import numpy as np
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from unittest.mock import Mock

try:
    import tensorflow as tf
except ImportError:
    # For testing purposes, create a mock TensorFlow
    tf = None

from backend.core.base_service import BaseProcessingService
from backend.core.interfaces import IEmotionAnalysisService
from backend.models.emotion import EmotionResult, EmotionStatistics, EmotionType
from backend.services.engagement_scoring import EngagementScoringAlgorithm, RealTimeEngagementTracker
from backend.services.websocket_integration_service import get_websocket_integration


class EmotionAnalysisService(BaseProcessingService, IEmotionAnalysisService):
    """Service for analyzing emotions from facial expressions."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.model = None
        self.emotion_mapping = {
            0: EmotionType.INTERESTED,
            1: EmotionType.BORED, 
            2: EmotionType.CONFUSED
        }
        self.confidence_threshold = 0.6
        self.session_statistics = {}
        self.websocket_integration = get_websocket_integration()
        
        # Initialize engagement scoring components
        self.engagement_algorithm = EngagementScoringAlgorithm()
        self.real_time_tracker = RealTimeEngagementTracker()
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the emotion classification model."""
        try:
            # For now, create a simple CNN model for emotion classification
            # In production, this would load a pre-trained model
            self.model = self._create_emotion_model()
            self.logger.info("Emotion analysis model initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize emotion model: {e}")
            raise
    
    def _create_emotion_model(self):
        """Create a simple CNN model for emotion classification."""
        if tf is None:
            # Return a mock model for testing
            return Mock()
            
        model = tf.keras.Sequential([
            tf.keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(48, 48, 1)),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
            tf.keras.layers.MaxPooling2D((2, 2)),
            tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dropout(0.5),
            tf.keras.layers.Dense(3, activation='softmax')  # 3 emotion classes
        ])
        
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def _preprocess_face(self, face_roi: np.ndarray) -> np.ndarray:
        """Preprocess face region for emotion analysis."""
        try:
            # Convert to grayscale if needed
            if len(face_roi.shape) == 3:
                face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            else:
                face_gray = face_roi
            
            # Resize to model input size (48x48)
            face_resized = cv2.resize(face_gray, (48, 48))
            
            # Normalize pixel values
            face_normalized = face_resized.astype('float32') / 255.0
            
            # Add batch and channel dimensions
            face_processed = np.expand_dims(face_normalized, axis=0)
            face_processed = np.expand_dims(face_processed, axis=-1)
            
            return face_processed
            
        except Exception as e:
            self.logger.error(f"Face preprocessing failed: {e}")
            raise
    
    def _classify_emotion(self, face_processed: np.ndarray) -> tuple[EmotionType, float]:
        """Classify emotion from preprocessed face."""
        try:
            # Get model predictions
            predictions = self.model.predict(face_processed, verbose=0)
            
            # Get the class with highest probability
            emotion_idx = np.argmax(predictions[0])
            confidence = float(predictions[0][emotion_idx])
            
            # Map to emotion type
            emotion = self.emotion_mapping[emotion_idx]
            
            return emotion, confidence
            
        except Exception as e:
            self.logger.error(f"Emotion classification failed: {e}")
            return EmotionType.CONFUSED, 0.0
    
    def _calculate_engagement_from_emotion(self, emotion: EmotionType, confidence: float) -> float:
        """Calculate engagement score from emotion and confidence."""
        # Engagement scoring logic:
        # Interested: High engagement (0.7-1.0)
        # Confused: Medium engagement (0.4-0.7) - at least paying attention
        # Bored: Low engagement (0.0-0.4)
        
        base_scores = {
            EmotionType.INTERESTED: 0.85,
            EmotionType.CONFUSED: 0.55,
            EmotionType.BORED: 0.25
        }
        
        base_score = base_scores[emotion]
        
        # Adjust based on confidence
        confidence_factor = confidence * 0.3  # Max 30% adjustment
        engagement_score = base_score + (confidence_factor if emotion == EmotionType.INTERESTED else -confidence_factor)
        
        # Clamp to valid range
        return max(0.0, min(1.0, engagement_score))
    
    def analyze_emotion(self, face_roi: np.ndarray, student_id: str = "unknown") -> EmotionResult:
        """Analyze emotion from face region of interest."""
        try:
            # Validate input
            if face_roi is None or face_roi.size == 0:
                raise ValueError("Invalid face ROI provided")
            
            # Preprocess face
            face_processed = self._preprocess_face(face_roi)
            
            # Classify emotion
            emotion, confidence = self._classify_emotion(face_processed)
            
            # Calculate engagement score
            engagement_score = self._calculate_engagement_from_emotion(emotion, confidence)
            
            # Create result
            result = EmotionResult(
                student_id=student_id,
                emotion=emotion,
                confidence=confidence,
                timestamp=datetime.now(),
                engagement_score=engagement_score
            )
            
            # Update processing stats
            self._update_stats(success=confidence >= self.confidence_threshold)
            
            self.logger.debug(f"Emotion analysis completed: {emotion.value} (confidence: {confidence:.2f})")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Emotion analysis failed: {e}")
            self._update_stats(success=False)
            
            # Return default result on failure
            return EmotionResult(
                student_id=student_id,
                emotion=EmotionType.CONFUSED,
                confidence=0.0,
                timestamp=datetime.now(),
                engagement_score=0.5
            )
    
    def validate_emotion_result(self, result: EmotionResult) -> bool:
        """Validate emotion analysis result."""
        try:
            # Check confidence threshold
            if result.confidence < self.confidence_threshold:
                self.logger.warning(f"Low confidence emotion result: {result.confidence}")
                return False
            
            # Check engagement score range
            if not (0.0 <= result.engagement_score <= 1.0):
                self.logger.error(f"Invalid engagement score: {result.engagement_score}")
                return False
            
            # Check timestamp is recent (within last 10 seconds)
            time_diff = (datetime.now() - result.timestamp).total_seconds()
            if time_diff > 10:
                self.logger.warning(f"Stale emotion result: {time_diff}s old")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Emotion result validation failed: {e}")
            return False
    
    def calculate_engagement_score(self, emotions: List[EmotionResult]) -> float:
        """Calculate overall engagement score from multiple emotion results."""
        if not emotions:
            return 0.0
        
        try:
            # Filter valid results
            valid_emotions = [e for e in emotions if self.validate_emotion_result(e)]
            
            if not valid_emotions:
                self.logger.warning("No valid emotion results for engagement calculation")
                return 0.0
            
            # Use advanced engagement scoring algorithm
            engagement_score, detailed_metrics = self.engagement_algorithm.calculate_engagement_score(valid_emotions)
            
            self.logger.debug(f"Calculated engagement score: {engagement_score:.2f} from {len(valid_emotions)} emotions")
            self.logger.debug(f"Detailed metrics: {detailed_metrics}")
            
            return engagement_score
            
        except Exception as e:
            self.logger.error(f"Engagement score calculation failed: {e}")
            return 0.0
    
    def get_session_statistics(self, session_id: str) -> EmotionStatistics:
        """Get emotion statistics for a session."""
        if session_id not in self.session_statistics:
            return EmotionStatistics(
                session_id=session_id,
                total_frames=0,
                emotion_counts={},
                emotion_percentages={},
                average_engagement_score=0.0,
                emotion_timeline=[]
            )
        
        return self.session_statistics[session_id]
    
    def update_session_statistics(self, session_id: str, emotion_result: EmotionResult):
        """Update session statistics with new emotion result."""
        try:
            if session_id not in self.session_statistics:
                self.session_statistics[session_id] = EmotionStatistics(
                    session_id=session_id,
                    total_frames=0,
                    emotion_counts={emotion: 0 for emotion in EmotionType},
                    emotion_percentages={emotion: 0.0 for emotion in EmotionType},
                    average_engagement_score=0.0,
                    emotion_timeline=[]
                )
            
            stats = self.session_statistics[session_id]
            
            # Update counts
            stats.total_frames += 1
            stats.emotion_counts[emotion_result.emotion] += 1
            
            # Update percentages
            for emotion in EmotionType:
                stats.emotion_percentages[emotion] = (
                    stats.emotion_counts[emotion] / stats.total_frames * 100
                )
            
            # Update average engagement score using advanced algorithm
            stats.emotion_timeline.append(emotion_result)
            stats.average_engagement_score = self.calculate_engagement_score(stats.emotion_timeline)
            
            # Update real-time tracker
            self.real_time_tracker.add_emotion_result(session_id, emotion_result)
            
            # Broadcast emotion update via WebSocket (async call in background)
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.websocket_integration.broadcast_emotion_update(session_id, stats))
            except Exception as ws_error:
                self.logger.warning(f"Failed to broadcast emotion update: {ws_error}")
            
            self.logger.debug(f"Updated session {session_id} statistics: {stats.total_frames} frames")
            
        except Exception as e:
            self.logger.error(f"Failed to update session statistics: {e}")
    
    def get_real_time_metrics(self, session_id: str) -> Optional[Dict]:
        """Get real-time engagement metrics for a session."""
        return self.real_time_tracker.get_current_metrics(session_id)
    
    def get_active_sessions(self) -> List[str]:
        """Get list of all active session IDs."""
        return self.real_time_tracker.get_all_active_sessions()
    
    def calculate_detailed_engagement_metrics(self, emotions: List[EmotionResult]) -> Dict[str, Any]:
        """Calculate detailed engagement metrics with pattern analysis."""
        if not emotions:
            return {"error": "No emotions provided"}
        
        try:
            engagement_score, detailed_metrics = self.engagement_algorithm.calculate_engagement_score(emotions)
            return detailed_metrics
        except Exception as e:
            self.logger.error(f"Detailed engagement metrics calculation failed: {e}")
            return {"error": str(e)}
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old inactive sessions."""
        self.real_time_tracker.cleanup_inactive_sessions(max_age_hours)
    
    def health_check(self) -> dict:
        """Health check for emotion analysis service."""
        base_health = super().health_check()
        
        emotion_health = {
            "model_loaded": self.model is not None,
            "confidence_threshold": self.confidence_threshold,
            "active_sessions": len(self.session_statistics),
            "processing_stats": self.get_processing_stats()
        }
        
        base_health.update(emotion_health)
        return base_health
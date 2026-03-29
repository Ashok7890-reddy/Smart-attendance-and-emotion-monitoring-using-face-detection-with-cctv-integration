"""
Lightweight Emotion Analysis Service

This service provides emotion analysis using OpenCV and a lightweight CNN model
as an alternative to DeepFace when it's not available or has compatibility issues.
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime
import logging

try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    tf = None
    keras = None

from backend.core.base_service import BaseProcessingService
from backend.models.emotion import EmotionResult, EmotionType


class LightweightEmotionService(BaseProcessingService):
    """Lightweight emotion analysis service using OpenCV and basic CNN."""
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Emotion mapping
        self.emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
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
            'happy': 0.90,
            'surprise': 0.80,
            'neutral': 0.50,
            'sad': 0.25,
            'angry': 0.35,
            'disgust': 0.20,
            'fear': 0.30
        }
        
        self.confidence_threshold = 0.6
        self.model = None
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the lightweight emotion model."""
        try:
            if TF_AVAILABLE:
                self.model = self._create_simple_emotion_model()
                self.logger.info("✅ Lightweight emotion model initialized")
            else:
                self.logger.warning("⚠️ TensorFlow not available, using rule-based emotion detection")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize emotion model: {e}")
            self.model = None
    
    def _create_simple_emotion_model(self):
        """Create a simple CNN model for emotion classification."""
        if not TF_AVAILABLE:
            return None
            
        try:
            model = keras.Sequential([
                keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(48, 48, 1)),
                keras.layers.MaxPooling2D((2, 2)),
                keras.layers.Conv2D(64, (3, 3), activation='relu'),
                keras.layers.MaxPooling2D((2, 2)),
                keras.layers.Conv2D(64, (3, 3), activation='relu'),
                keras.layers.Flatten(),
                keras.layers.Dense(64, activation='relu'),
                keras.layers.Dropout(0.5),
                keras.layers.Dense(7, activation='softmax')  # 7 emotions
            ])
            
            model.compile(
                optimizer='adam',
                loss='categorical_crossentropy',
                metrics=['accuracy']
            )
            
            # Initialize with random weights (in production, load pre-trained weights)
            dummy_input = np.random.random((1, 48, 48, 1))
            model.predict(dummy_input, verbose=0)
            
            return model
            
        except Exception as e:
            self.logger.error(f"Failed to create emotion model: {e}")
            return None
    
    def _preprocess_face(self, face_roi: np.ndarray) -> np.ndarray:
        """Preprocess face region for emotion analysis."""
        try:
            # Convert to grayscale if needed
            if len(face_roi.shape) == 3:
                face_gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            else:
                face_gray = face_roi
            
            # Resize to model input size
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
    
    def _rule_based_emotion_detection(self, face_roi: np.ndarray) -> Dict[str, float]:
        """Simple rule-based emotion detection using image statistics."""
        try:
            # Convert to grayscale
            if len(face_roi.shape) == 3:
                gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            else:
                gray = face_roi
            
            # Calculate basic image statistics
            mean_intensity = np.mean(gray)
            std_intensity = np.std(gray)
            
            # Simple heuristics based on image properties
            emotions = {
                'neutral': 0.4,  # Base probability
                'happy': 0.0,
                'sad': 0.0,
                'angry': 0.0,
                'surprise': 0.0,
                'fear': 0.0,
                'disgust': 0.0
            }
            
            # Brightness-based heuristics
            if mean_intensity > 120:
                emotions['happy'] += 0.3
                emotions['surprise'] += 0.2
            elif mean_intensity < 80:
                emotions['sad'] += 0.3
                emotions['angry'] += 0.2
            
            # Contrast-based heuristics
            if std_intensity > 50:
                emotions['surprise'] += 0.2
                emotions['fear'] += 0.1
            elif std_intensity < 20:
                emotions['sad'] += 0.2
                emotions['neutral'] += 0.1
            
            # Normalize probabilities
            total = sum(emotions.values())
            if total > 0:
                emotions = {k: v/total for k, v in emotions.items()}
            
            return emotions
            
        except Exception as e:
            self.logger.error(f"Rule-based emotion detection failed: {e}")
            return {'neutral': 1.0}
    
    def analyze_emotion_from_base64(self, base64_image: str, student_id: str = "unknown") -> Dict[str, Any]:
        """Analyze emotion from base64 encoded image."""
        try:
            import base64
            import io
            from PIL import Image
            
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
    
    def analyze_emotion(self, face_roi: np.ndarray, student_id: str = "unknown") -> Dict[str, Any]:
        """Analyze emotion from face region of interest."""
        try:
            # Validate input
            if face_roi is None or face_roi.size == 0:
                raise ValueError("Invalid face ROI provided")
            
            # Get emotion probabilities
            if self.model is not None:
                # Use CNN model
                face_processed = self._preprocess_face(face_roi)
                predictions = self.model.predict(face_processed, verbose=0)
                emotion_probs = predictions[0]
                
                # Create emotion dictionary
                emotion_data = {
                    emotion: float(prob * 100) 
                    for emotion, prob in zip(self.emotion_labels, emotion_probs)
                }
            else:
                # Use rule-based detection
                emotion_probs_dict = self._rule_based_emotion_detection(face_roi)
                emotion_data = {
                    emotion: prob * 100 
                    for emotion, prob in emotion_probs_dict.items()
                }
            
            # Find dominant emotion
            dominant_emotion = max(emotion_data, key=emotion_data.get)
            confidence = emotion_data[dominant_emotion] / 100.0
            
            # Map to engagement level
            engagement_type = self.emotion_to_engagement.get(dominant_emotion, EmotionType.BORED)
            
            # Calculate engagement score
            engagement_score = self._calculate_engagement_score(emotion_data)
            
            # Create result
            result = {
                "success": True,
                "student_id": student_id,
                "emotion": engagement_type.value,
                "raw_emotion": dominant_emotion,
                "confidence": confidence,
                "engagement_score": engagement_score,
                "timestamp": datetime.now().isoformat(),
                "emotion_breakdown": {
                    "raw_emotions": emotion_data,
                    "dominant_emotion": dominant_emotion,
                    "engagement_distribution": self._calculate_engagement_distribution(emotion_data)
                }
            }
            
            self.logger.debug(f"Lightweight emotion analysis: {dominant_emotion} ({confidence:.2f})")
            return result
            
        except Exception as e:
            self.logger.error(f"Emotion analysis failed: {e}")
            return self._create_fallback_result(student_id)
    
    def _calculate_engagement_score(self, emotion_data: Dict[str, float]) -> float:
        """Calculate engagement score from emotion probabilities."""
        try:
            total_score = 0.0
            total_weight = 0.0
            
            for emotion, percentage in emotion_data.items():
                weight = self.engagement_weights.get(emotion, 0.5)
                normalized_prob = percentage / 100.0
                total_score += weight * normalized_prob
                total_weight += normalized_prob
            
            if total_weight > 0:
                engagement_score = total_score / total_weight
            else:
                engagement_score = 0.5
            
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
            
            emotion_to_engagement_str = {
                'happy': 'interested',
                'surprise': 'interested',
                'neutral': 'bored',
                'sad': 'sleepy',
                'angry': 'confused',
                'disgust': 'bored',
                'fear': 'confused'
            }
            
            for emotion, percentage in emotion_data.items():
                engagement_level = emotion_to_engagement_str.get(emotion, 'bored')
                engagement_dist[engagement_level] += percentage / 100.0
            
            return engagement_dist
            
        except Exception as e:
            self.logger.error(f"Engagement distribution calculation failed: {e}")
            return {'interested': 0.25, 'bored': 0.25, 'confused': 0.25, 'sleepy': 0.25}
    
    def _create_fallback_result(self, student_id: str) -> Dict[str, Any]:
        """Create fallback result when analysis fails."""
        return {
            "success": False,
            "student_id": student_id,
            "emotion": "bored",
            "raw_emotion": "neutral",
            "confidence": 0.5,
            "engagement_score": 0.5,
            "timestamp": datetime.now().isoformat(),
            "emotion_breakdown": {
                "raw_emotions": {"neutral": 100.0},
                "dominant_emotion": "neutral",
                "engagement_distribution": {"interested": 0.0, "bored": 1.0, "confused": 0.0, "sleepy": 0.0}
            }
        }
    
    def health_check(self) -> dict:
        """Health check for lightweight emotion service."""
        base_health = super().health_check()
        
        emotion_health = {
            "tensorflow_available": TF_AVAILABLE,
            "model_loaded": self.model is not None,
            "confidence_threshold": self.confidence_threshold,
            "detection_method": "cnn_model" if self.model else "rule_based"
        }
        
        base_health.update(emotion_health)
        return base_health


# Create global instance
lightweight_emotion_service = LightweightEmotionService()
"""
Engagement Scoring Algorithm for the Smart Attendance System.

This module implements sophisticated engagement scoring based on emotion patterns,
frame-wise statistics aggregation, and real-time metrics computation.
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from collections import deque
import logging

from backend.models.emotion import EmotionResult, EmotionType, EmotionStatistics


class EngagementScoringAlgorithm:
    """Advanced engagement scoring algorithm based on emotion patterns."""
    
    def __init__(self, window_size: int = 30, decay_factor: float = 0.95):
        """
        Initialize engagement scoring algorithm.
        
        Args:
            window_size: Number of recent frames to consider for scoring
            decay_factor: Decay factor for temporal weighting (0-1)
        """
        self.window_size = window_size
        self.decay_factor = decay_factor
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Emotion weights for engagement calculation
        self.emotion_weights = {
            EmotionType.INTERESTED: 1.0,
            EmotionType.CONFUSED: 0.6,  # Still engaged but struggling
            EmotionType.BORED: 0.1      # Low engagement
        }
        
        # Pattern bonuses for sustained emotions
        self.pattern_bonuses = {
            EmotionType.INTERESTED: 0.2,  # Bonus for sustained interest
            EmotionType.CONFUSED: 0.1,    # Small bonus for sustained confusion (deep thinking)
            EmotionType.BORED: -0.3       # Penalty for sustained boredom
        }
    
    def calculate_base_engagement(self, emotion: EmotionType, confidence: float) -> float:
        """Calculate base engagement score for a single emotion."""
        base_score = self.emotion_weights[emotion]
        confidence_adjusted = base_score * confidence
        
        # Apply non-linear scaling for more realistic scores
        if emotion == EmotionType.INTERESTED:
            # Boost high-confidence interest
            confidence_adjusted = min(1.0, confidence_adjusted * 1.2)
        elif emotion == EmotionType.BORED:
            # Penalize high-confidence boredom more severely
            confidence_adjusted = max(0.0, confidence_adjusted * 0.8)
        
        return confidence_adjusted
    
    def calculate_temporal_weights(self, num_frames: int) -> np.ndarray:
        """Calculate temporal weights with exponential decay."""
        weights = np.array([self.decay_factor ** i for i in range(num_frames)])
        # Reverse so recent frames have higher weights
        weights = weights[::-1]
        # Normalize weights
        return weights / weights.sum()
    
    def detect_emotion_patterns(self, emotions: List[EmotionResult]) -> Dict[str, float]:
        """Detect patterns in emotion sequence and calculate pattern scores."""
        if len(emotions) < 3:
            return {"pattern_score": 0.0, "consistency": 0.0, "trend": 0.0}
        
        # Extract emotion sequence
        emotion_sequence = [e.emotion for e in emotions]
        
        # Calculate consistency (how often the same emotion appears)
        emotion_counts = {}
        for emotion in emotion_sequence:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        max_count = max(emotion_counts.values())
        consistency = max_count / len(emotion_sequence)
        
        # Calculate trend (improvement/decline in engagement)
        engagement_scores = [self.calculate_base_engagement(e.emotion, e.confidence) for e in emotions]
        
        if len(engagement_scores) >= 5:
            # Use linear regression to detect trend
            x = np.arange(len(engagement_scores))
            y = np.array(engagement_scores)
            trend = np.polyfit(x, y, 1)[0]  # Slope of the trend line
        else:
            # Simple comparison for short sequences
            trend = (engagement_scores[-1] - engagement_scores[0]) / len(engagement_scores)
        
        # Calculate pattern bonus based on dominant emotion
        dominant_emotion = max(emotion_counts, key=emotion_counts.get)
        pattern_bonus = self.pattern_bonuses[dominant_emotion] * consistency
        
        return {
            "pattern_score": pattern_bonus,
            "consistency": consistency,
            "trend": trend,
            "dominant_emotion": dominant_emotion.value
        }
    
    def calculate_engagement_score(self, emotions: List[EmotionResult]) -> Tuple[float, Dict[str, float]]:
        """
        Calculate comprehensive engagement score with detailed metrics.
        
        Returns:
            Tuple of (engagement_score, metrics_dict)
        """
        if not emotions:
            return 0.0, {"error": "No emotions provided"}
        
        try:
            # Limit to recent frames
            recent_emotions = emotions[-self.window_size:] if len(emotions) > self.window_size else emotions
            
            # Calculate base engagement scores
            base_scores = [
                self.calculate_base_engagement(e.emotion, e.confidence) 
                for e in recent_emotions
            ]
            
            # Apply temporal weighting
            temporal_weights = self.calculate_temporal_weights(len(base_scores))
            weighted_score = np.average(base_scores, weights=temporal_weights)
            
            # Detect patterns and apply bonuses
            pattern_metrics = self.detect_emotion_patterns(recent_emotions)
            pattern_adjusted_score = weighted_score + pattern_metrics["pattern_score"]
            
            # Apply trend adjustment
            trend_adjustment = pattern_metrics["trend"] * 0.1  # Small trend influence
            final_score = pattern_adjusted_score + trend_adjustment
            
            # Clamp to valid range
            final_score = max(0.0, min(1.0, final_score))
            
            # Compile detailed metrics
            metrics = {
                "base_score": float(weighted_score),
                "pattern_bonus": float(pattern_metrics["pattern_score"]),
                "trend_adjustment": float(trend_adjustment),
                "final_score": float(final_score),
                "consistency": float(pattern_metrics["consistency"]),
                "trend": float(pattern_metrics["trend"]),
                "dominant_emotion": pattern_metrics["dominant_emotion"],
                "frames_analyzed": len(recent_emotions),
                "confidence_avg": float(np.mean([e.confidence for e in recent_emotions]))
            }
            
            return final_score, metrics
            
        except Exception as e:
            self.logger.error(f"Engagement score calculation failed: {e}")
            return 0.0, {"error": str(e)}


class RealTimeEngagementTracker:
    """Real-time engagement metrics computation and tracking."""
    
    def __init__(self, update_interval: int = 5):
        """
        Initialize real-time engagement tracker.
        
        Args:
            update_interval: Seconds between metric updates
        """
        self.update_interval = update_interval
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Session tracking
        self.session_data = {}
        self.scoring_algorithm = EngagementScoringAlgorithm()
        
        # Real-time metrics
        self.current_metrics = {}
        self.last_update = {}
    
    def add_emotion_result(self, session_id: str, emotion_result: EmotionResult):
        """Add new emotion result to session tracking."""
        if session_id not in self.session_data:
            self.session_data[session_id] = {
                "emotions": deque(maxlen=100),  # Keep last 100 emotions
                "start_time": datetime.now(),
                "last_activity": datetime.now()
            }
        
        session = self.session_data[session_id]
        session["emotions"].append(emotion_result)
        session["last_activity"] = datetime.now()
        
        # Update metrics if enough time has passed
        self._maybe_update_metrics(session_id)
    
    def _maybe_update_metrics(self, session_id: str):
        """Update metrics if update interval has passed."""
        now = datetime.now()
        
        if (session_id not in self.last_update or 
            (now - self.last_update[session_id]).seconds >= self.update_interval):
            
            self._update_session_metrics(session_id)
            self.last_update[session_id] = now
    
    def _update_session_metrics(self, session_id: str):
        """Update real-time metrics for a session."""
        try:
            if session_id not in self.session_data:
                return
            
            session = self.session_data[session_id]
            emotions = list(session["emotions"])
            
            if not emotions:
                return
            
            # Calculate engagement score and metrics
            engagement_score, detailed_metrics = self.scoring_algorithm.calculate_engagement_score(emotions)
            
            # Calculate additional real-time metrics
            recent_emotions = emotions[-10:]  # Last 10 emotions
            emotion_distribution = self._calculate_emotion_distribution(recent_emotions)
            
            # Calculate engagement trend (last 30 seconds)
            trend_emotions = [e for e in emotions 
                            if (datetime.now() - e.timestamp).seconds <= 30]
            engagement_trend = self._calculate_engagement_trend(trend_emotions)
            
            # Update current metrics
            self.current_metrics[session_id] = {
                "timestamp": datetime.now(),
                "engagement_score": engagement_score,
                "emotion_distribution": emotion_distribution,
                "engagement_trend": engagement_trend,
                "total_frames": len(emotions),
                "session_duration": (datetime.now() - session["start_time"]).seconds,
                "detailed_metrics": detailed_metrics
            }
            
            self.logger.debug(f"Updated metrics for session {session_id}: {engagement_score:.2f}")
            
        except Exception as e:
            self.logger.error(f"Failed to update session metrics: {e}")
    
    def _calculate_emotion_distribution(self, emotions: List[EmotionResult]) -> Dict[str, float]:
        """Calculate emotion distribution percentages."""
        if not emotions:
            return {emotion.value: 0.0 for emotion in EmotionType}
        
        emotion_counts = {emotion.value: 0 for emotion in EmotionType}
        
        for emotion_result in emotions:
            emotion_counts[emotion_result.emotion.value] += 1
        
        total = len(emotions)
        return {emotion: (count / total) * 100 for emotion, count in emotion_counts.items()}
    
    def _calculate_engagement_trend(self, emotions: List[EmotionResult]) -> str:
        """Calculate engagement trend (improving, declining, stable)."""
        if len(emotions) < 5:
            return "insufficient_data"
        
        # Split into two halves and compare average engagement
        mid_point = len(emotions) // 2
        first_half = emotions[:mid_point]
        second_half = emotions[mid_point:]
        
        first_avg = np.mean([
            self.scoring_algorithm.calculate_base_engagement(e.emotion, e.confidence) 
            for e in first_half
        ])
        
        second_avg = np.mean([
            self.scoring_algorithm.calculate_base_engagement(e.emotion, e.confidence) 
            for e in second_half
        ])
        
        diff = second_avg - first_avg
        
        if diff > 0.1:
            return "improving"
        elif diff < -0.1:
            return "declining"
        else:
            return "stable"
    
    def get_current_metrics(self, session_id: str) -> Optional[Dict]:
        """Get current real-time metrics for a session."""
        return self.current_metrics.get(session_id)
    
    def get_all_active_sessions(self) -> List[str]:
        """Get list of all active session IDs."""
        now = datetime.now()
        active_sessions = []
        
        for session_id, session in self.session_data.items():
            # Consider session active if last activity was within 5 minutes
            if (now - session["last_activity"]).seconds <= 300:
                active_sessions.append(session_id)
        
        return active_sessions
    
    def cleanup_inactive_sessions(self, max_age_hours: int = 24):
        """Clean up old inactive sessions."""
        now = datetime.now()
        cutoff_time = now - timedelta(hours=max_age_hours)
        
        inactive_sessions = [
            session_id for session_id, session in self.session_data.items()
            if session["last_activity"] < cutoff_time
        ]
        
        for session_id in inactive_sessions:
            del self.session_data[session_id]
            if session_id in self.current_metrics:
                del self.current_metrics[session_id]
            if session_id in self.last_update:
                del self.last_update[session_id]
        
        if inactive_sessions:
            self.logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")
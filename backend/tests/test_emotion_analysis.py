"""
Unit tests for emotion analysis service and engagement scoring.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import List
import sys

# Mock TensorFlow to avoid import issues during testing
sys.modules['tensorflow'] = Mock()
sys.modules['tensorflow.keras'] = Mock()
sys.modules['tensorflow.keras.Sequential'] = Mock()
sys.modules['tensorflow.keras.layers'] = Mock()

from backend.services.emotion_analysis_service import EmotionAnalysisService
from backend.services.engagement_scoring import EngagementScoringAlgorithm, RealTimeEngagementTracker
from backend.models.emotion import EmotionResult, EmotionType, EmotionStatistics
from backend.core.config import Config


class TestEmotionAnalysisService:
    """Test cases for EmotionAnalysisService."""
    
    @pytest.fixture
    def emotion_service(self):
        """Create emotion analysis service for testing."""
        config = Config()
        service = EmotionAnalysisService(config)
        # Mock the model to avoid loading actual TensorFlow model
        service.model = Mock()
        return service
    
    @pytest.fixture
    def sample_face_roi(self):
        """Create sample face ROI for testing."""
        # Create a 100x100 RGB face image
        return np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    
    @pytest.fixture
    def sample_emotion_results(self):
        """Create sample emotion results for testing."""
        base_time = datetime.now()
        return [
            EmotionResult(
                student_id="STU001",
                emotion=EmotionType.INTERESTED,
                confidence=0.9,
                timestamp=base_time,
                engagement_score=0.85
            ),
            EmotionResult(
                student_id="STU001", 
                emotion=EmotionType.INTERESTED,
                confidence=0.8,
                timestamp=base_time + timedelta(seconds=1),
                engagement_score=0.8
            ),
            EmotionResult(
                student_id="STU001",
                emotion=EmotionType.BORED,
                confidence=0.7,
                timestamp=base_time + timedelta(seconds=2),
                engagement_score=0.3
            ),
            EmotionResult(
                student_id="STU001",
                emotion=EmotionType.CONFUSED,
                confidence=0.85,
                timestamp=base_time + timedelta(seconds=3),
                engagement_score=0.6
            )
        ]
    
    def test_preprocess_face_rgb_input(self, emotion_service, sample_face_roi):
        """Test face preprocessing with RGB input."""
        processed = emotion_service._preprocess_face(sample_face_roi)
        
        # Check output shape (batch_size=1, height=48, width=48, channels=1)
        assert processed.shape == (1, 48, 48, 1)
        
        # Check normalization (values should be between 0 and 1)
        assert processed.min() >= 0.0
        assert processed.max() <= 1.0
    
    def test_preprocess_face_grayscale_input(self, emotion_service):
        """Test face preprocessing with grayscale input."""
        # Create grayscale face image
        face_gray = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        processed = emotion_service._preprocess_face(face_gray)
        
        assert processed.shape == (1, 48, 48, 1)
        assert processed.min() >= 0.0
        assert processed.max() <= 1.0
    
    def test_preprocess_face_invalid_input(self, emotion_service):
        """Test face preprocessing with invalid input."""
        with pytest.raises(Exception):
            emotion_service._preprocess_face(np.array([]))
    
    def test_classify_emotion(self, emotion_service):
        """Test emotion classification."""
        # Mock model prediction
        mock_predictions = np.array([[0.1, 0.2, 0.7]])  # Confused emotion
        emotion_service.model.predict.return_value = mock_predictions
        
        face_processed = np.random.rand(1, 48, 48, 1)
        emotion, confidence = emotion_service._classify_emotion(face_processed)
        
        assert emotion == EmotionType.CONFUSED
        assert confidence == 0.7
        emotion_service.model.predict.assert_called_once()
    
    def test_calculate_engagement_from_emotion(self, emotion_service):
        """Test engagement score calculation from emotion."""
        # Test interested emotion
        score = emotion_service._calculate_engagement_from_emotion(EmotionType.INTERESTED, 0.9)
        assert 0.7 <= score <= 1.0
        
        # Test bored emotion
        score = emotion_service._calculate_engagement_from_emotion(EmotionType.BORED, 0.8)
        assert 0.0 <= score <= 0.4
        
        # Test confused emotion
        score = emotion_service._calculate_engagement_from_emotion(EmotionType.CONFUSED, 0.7)
        assert 0.3 <= score <= 0.7
    
    def test_analyze_emotion_success(self, emotion_service, sample_face_roi):
        """Test successful emotion analysis."""
        # Mock model prediction
        mock_predictions = np.array([[0.8, 0.1, 0.1]])  # Interested emotion
        emotion_service.model.predict.return_value = mock_predictions
        
        result = emotion_service.analyze_emotion(sample_face_roi, "STU001")
        
        assert result.student_id == "STU001"
        assert result.emotion == EmotionType.INTERESTED
        assert result.confidence == 0.8
        assert 0.0 <= result.engagement_score <= 1.0
        assert isinstance(result.timestamp, datetime)
    
    def test_analyze_emotion_invalid_input(self, emotion_service):
        """Test emotion analysis with invalid input."""
        result = emotion_service.analyze_emotion(None, "STU001")
        
        # Should return default result on failure
        assert result.student_id == "STU001"
        assert result.emotion == EmotionType.CONFUSED
        assert result.confidence == 0.0
        assert result.engagement_score == 0.5
    
    def test_validate_emotion_result(self, emotion_service):
        """Test emotion result validation."""
        # Valid result
        valid_result = EmotionResult(
            student_id="STU001",
            emotion=EmotionType.INTERESTED,
            confidence=0.8,
            timestamp=datetime.now(),
            engagement_score=0.75
        )
        assert emotion_service.validate_emotion_result(valid_result) == True
        
        # Low confidence result
        low_confidence_result = EmotionResult(
            student_id="STU001",
            emotion=EmotionType.INTERESTED,
            confidence=0.3,  # Below threshold
            timestamp=datetime.now(),
            engagement_score=0.75
        )
        assert emotion_service.validate_emotion_result(low_confidence_result) == False
        
        # Invalid engagement score
        invalid_score_result = EmotionResult(
            student_id="STU001",
            emotion=EmotionType.INTERESTED,
            confidence=0.8,
            timestamp=datetime.now(),
            engagement_score=1.5  # Above 1.0
        )
        assert emotion_service.validate_emotion_result(invalid_score_result) == False
    
    def test_calculate_engagement_score_empty_list(self, emotion_service):
        """Test engagement score calculation with empty emotion list."""
        score = emotion_service.calculate_engagement_score([])
        assert score == 0.0
    
    def test_calculate_engagement_score_valid_emotions(self, emotion_service, sample_emotion_results):
        """Test engagement score calculation with valid emotions."""
        score = emotion_service.calculate_engagement_score(sample_emotion_results)
        
        # Should return a valid engagement score
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
    
    def test_update_session_statistics(self, emotion_service, sample_emotion_results):
        """Test session statistics update."""
        session_id = "TEST_SESSION"
        
        for emotion_result in sample_emotion_results:
            emotion_service.update_session_statistics(session_id, emotion_result)
        
        stats = emotion_service.get_session_statistics(session_id)
        
        assert stats.session_id == session_id
        assert stats.total_frames == len(sample_emotion_results)
        assert len(stats.emotion_timeline) == len(sample_emotion_results)
        assert 0.0 <= stats.average_engagement_score <= 1.0
        
        # Check emotion counts
        assert stats.emotion_counts[EmotionType.INTERESTED] == 2
        assert stats.emotion_counts[EmotionType.BORED] == 1
        assert stats.emotion_counts[EmotionType.CONFUSED] == 1
    
    def test_get_real_time_metrics(self, emotion_service):
        """Test real-time metrics retrieval."""
        session_id = "TEST_SESSION"
        
        # Add some emotion results
        emotion_result = EmotionResult(
            student_id="STU001",
            emotion=EmotionType.INTERESTED,
            confidence=0.8,
            timestamp=datetime.now(),
            engagement_score=0.8
        )
        
        emotion_service.update_session_statistics(session_id, emotion_result)
        
        # Get metrics (might be None if not enough time passed)
        metrics = emotion_service.get_real_time_metrics(session_id)
        
        # Metrics might be None due to update interval, which is expected
        if metrics:
            assert "engagement_score" in metrics
            assert "emotion_distribution" in metrics
    
    def test_health_check(self, emotion_service):
        """Test service health check."""
        health = emotion_service.health_check()
        
        assert "service" in health
        assert "model_loaded" in health
        assert "confidence_threshold" in health
        assert "processing_stats" in health
        assert health["model_loaded"] == True


class TestEngagementScoringAlgorithm:
    """Test cases for EngagementScoringAlgorithm."""
    
    @pytest.fixture
    def scoring_algorithm(self):
        """Create engagement scoring algorithm for testing."""
        return EngagementScoringAlgorithm(window_size=10, decay_factor=0.9)
    
    @pytest.fixture
    def sample_emotions_sequence(self):
        """Create sample emotion sequence for testing."""
        base_time = datetime.now()
        emotions = []
        
        # Create a sequence showing declining engagement
        emotion_types = [EmotionType.INTERESTED] * 3 + [EmotionType.CONFUSED] * 2 + [EmotionType.BORED] * 3
        
        for i, emotion_type in enumerate(emotion_types):
            emotions.append(EmotionResult(
                student_id="STU001",
                emotion=emotion_type,
                confidence=0.8,
                timestamp=base_time + timedelta(seconds=i),
                engagement_score=0.0  # Will be calculated
            ))
        
        return emotions
    
    def test_calculate_base_engagement(self, scoring_algorithm):
        """Test base engagement calculation."""
        # Test interested emotion
        score = scoring_algorithm.calculate_base_engagement(EmotionType.INTERESTED, 0.9)
        assert score > 0.8  # Should be high
        
        # Test bored emotion
        score = scoring_algorithm.calculate_base_engagement(EmotionType.BORED, 0.9)
        assert score < 0.2  # Should be low
        
        # Test confused emotion
        score = scoring_algorithm.calculate_base_engagement(EmotionType.CONFUSED, 0.8)
        assert 0.3 < score < 0.7  # Should be medium
    
    def test_calculate_temporal_weights(self, scoring_algorithm):
        """Test temporal weight calculation."""
        weights = scoring_algorithm.calculate_temporal_weights(5)
        
        assert len(weights) == 5
        assert np.isclose(weights.sum(), 1.0)  # Should be normalized
        assert weights[-1] > weights[0]  # Recent frames should have higher weights
    
    def test_detect_emotion_patterns(self, scoring_algorithm, sample_emotions_sequence):
        """Test emotion pattern detection."""
        patterns = scoring_algorithm.detect_emotion_patterns(sample_emotions_sequence)
        
        assert "pattern_score" in patterns
        assert "consistency" in patterns
        assert "trend" in patterns
        assert "dominant_emotion" in patterns
        
        # Check consistency is reasonable
        assert 0.0 <= patterns["consistency"] <= 1.0
        
        # Check dominant emotion
        assert patterns["dominant_emotion"] in ["interested", "bored", "confused"]
    
    def test_calculate_engagement_score(self, scoring_algorithm, sample_emotions_sequence):
        """Test comprehensive engagement score calculation."""
        score, metrics = scoring_algorithm.calculate_engagement_score(sample_emotions_sequence)
        
        # Check score is valid
        assert 0.0 <= score <= 1.0
        
        # Check metrics
        assert "base_score" in metrics
        assert "pattern_bonus" in metrics
        assert "trend_adjustment" in metrics
        assert "final_score" in metrics
        assert "consistency" in metrics
        assert "frames_analyzed" in metrics
        
        # Final score should match returned score
        assert np.isclose(score, metrics["final_score"])
    
    def test_calculate_engagement_score_empty_list(self, scoring_algorithm):
        """Test engagement score calculation with empty list."""
        score, metrics = scoring_algorithm.calculate_engagement_score([])
        
        assert score == 0.0
        assert "error" in metrics


class TestRealTimeEngagementTracker:
    """Test cases for RealTimeEngagementTracker."""
    
    @pytest.fixture
    def engagement_tracker(self):
        """Create real-time engagement tracker for testing."""
        return RealTimeEngagementTracker(update_interval=1)  # 1 second for testing
    
    def test_add_emotion_result(self, engagement_tracker):
        """Test adding emotion result to tracker."""
        session_id = "TEST_SESSION"
        emotion_result = EmotionResult(
            student_id="STU001",
            emotion=EmotionType.INTERESTED,
            confidence=0.8,
            timestamp=datetime.now(),
            engagement_score=0.8
        )
        
        engagement_tracker.add_emotion_result(session_id, emotion_result)
        
        # Check session was created
        assert session_id in engagement_tracker.session_data
        assert len(engagement_tracker.session_data[session_id]["emotions"]) == 1
    
    def test_get_current_metrics(self, engagement_tracker):
        """Test getting current metrics."""
        session_id = "TEST_SESSION"
        
        # Add emotion result
        emotion_result = EmotionResult(
            student_id="STU001",
            emotion=EmotionType.INTERESTED,
            confidence=0.8,
            timestamp=datetime.now(),
            engagement_score=0.8
        )
        
        engagement_tracker.add_emotion_result(session_id, emotion_result)
        
        # Force metrics update
        engagement_tracker._update_session_metrics(session_id)
        
        metrics = engagement_tracker.get_current_metrics(session_id)
        
        if metrics:  # Metrics might not be available immediately
            assert "engagement_score" in metrics
            assert "emotion_distribution" in metrics
            assert "total_frames" in metrics
    
    def test_calculate_emotion_distribution(self, engagement_tracker):
        """Test emotion distribution calculation."""
        emotions = [
            EmotionResult("STU001", EmotionType.INTERESTED, 0.8, datetime.now(), 0.8),
            EmotionResult("STU001", EmotionType.INTERESTED, 0.7, datetime.now(), 0.7),
            EmotionResult("STU001", EmotionType.BORED, 0.6, datetime.now(), 0.3),
        ]
        
        distribution = engagement_tracker._calculate_emotion_distribution(emotions)
        
        assert "interested" in distribution
        assert "bored" in distribution
        assert "confused" in distribution
        
        # Check percentages sum to 100
        total_percentage = sum(distribution.values())
        assert np.isclose(total_percentage, 100.0)
        
        # Check specific percentages
        assert np.isclose(distribution["interested"], 66.67, atol=0.1)
        assert np.isclose(distribution["bored"], 33.33, atol=0.1)
        assert np.isclose(distribution["confused"], 0.0)
    
    def test_calculate_engagement_trend(self, engagement_tracker):
        """Test engagement trend calculation."""
        # Create emotions showing improvement
        improving_emotions = [
            EmotionResult("STU001", EmotionType.BORED, 0.8, datetime.now(), 0.2),
            EmotionResult("STU001", EmotionType.CONFUSED, 0.8, datetime.now(), 0.5),
            EmotionResult("STU001", EmotionType.INTERESTED, 0.8, datetime.now(), 0.8),
            EmotionResult("STU001", EmotionType.INTERESTED, 0.9, datetime.now(), 0.9),
            EmotionResult("STU001", EmotionType.INTERESTED, 0.9, datetime.now(), 0.9),
        ]
        
        trend = engagement_tracker._calculate_engagement_trend(improving_emotions)
        assert trend == "improving"
        
        # Create emotions showing decline
        declining_emotions = [
            EmotionResult("STU001", EmotionType.INTERESTED, 0.9, datetime.now(), 0.9),
            EmotionResult("STU001", EmotionType.INTERESTED, 0.8, datetime.now(), 0.8),
            EmotionResult("STU001", EmotionType.CONFUSED, 0.8, datetime.now(), 0.5),
            EmotionResult("STU001", EmotionType.BORED, 0.8, datetime.now(), 0.2),
            EmotionResult("STU001", EmotionType.BORED, 0.9, datetime.now(), 0.1),
        ]
        
        trend = engagement_tracker._calculate_engagement_trend(declining_emotions)
        assert trend == "declining"
    
    def test_get_all_active_sessions(self, engagement_tracker):
        """Test getting all active sessions."""
        # Add emotion to create session
        emotion_result = EmotionResult(
            student_id="STU001",
            emotion=EmotionType.INTERESTED,
            confidence=0.8,
            timestamp=datetime.now(),
            engagement_score=0.8
        )
        
        engagement_tracker.add_emotion_result("SESSION1", emotion_result)
        engagement_tracker.add_emotion_result("SESSION2", emotion_result)
        
        active_sessions = engagement_tracker.get_all_active_sessions()
        
        assert "SESSION1" in active_sessions
        assert "SESSION2" in active_sessions
    
    def test_cleanup_inactive_sessions(self, engagement_tracker):
        """Test cleanup of inactive sessions."""
        # Add old session
        old_emotion = EmotionResult(
            student_id="STU001",
            emotion=EmotionType.INTERESTED,
            confidence=0.8,
            timestamp=datetime.now() - timedelta(hours=25),  # Old timestamp
            engagement_score=0.8
        )
        
        engagement_tracker.add_emotion_result("OLD_SESSION", old_emotion)
        
        # Manually set old last_activity
        engagement_tracker.session_data["OLD_SESSION"]["last_activity"] = datetime.now() - timedelta(hours=25)
        
        # Add recent session
        recent_emotion = EmotionResult(
            student_id="STU001",
            emotion=EmotionType.INTERESTED,
            confidence=0.8,
            timestamp=datetime.now(),
            engagement_score=0.8
        )
        
        engagement_tracker.add_emotion_result("RECENT_SESSION", recent_emotion)
        
        # Cleanup
        engagement_tracker.cleanup_inactive_sessions(max_age_hours=24)
        
        # Old session should be removed, recent should remain
        assert "OLD_SESSION" not in engagement_tracker.session_data
        assert "RECENT_SESSION" in engagement_tracker.session_data


@pytest.mark.integration
class TestEmotionAnalysisIntegration:
    """Integration tests for emotion analysis components."""
    
    def test_full_emotion_analysis_workflow(self):
        """Test complete emotion analysis workflow."""
        # Create service
        config = Config()
        service = EmotionAnalysisService(config)
        service.model = Mock()
        
        # Mock model predictions for different emotions
        predictions = [
            np.array([[0.8, 0.1, 0.1]]),  # Interested
            np.array([[0.7, 0.2, 0.1]]),  # Interested
            np.array([[0.1, 0.8, 0.1]]),  # Bored
            np.array([[0.2, 0.1, 0.7]]),  # Confused
        ]
        
        service.model.predict.side_effect = predictions
        
        # Create sample face ROIs
        face_rois = [np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8) for _ in range(4)]
        
        session_id = "INTEGRATION_TEST"
        emotion_results = []
        
        # Process emotions
        for i, face_roi in enumerate(face_rois):
            result = service.analyze_emotion(face_roi, f"STU{i:03d}")
            emotion_results.append(result)
            service.update_session_statistics(session_id, result)
        
        # Check results
        assert len(emotion_results) == 4
        
        # Check session statistics
        stats = service.get_session_statistics(session_id)
        assert stats.total_frames == 4
        assert len(stats.emotion_timeline) == 4
        
        # Check engagement score calculation
        engagement_score = service.calculate_engagement_score(emotion_results)
        assert 0.0 <= engagement_score <= 1.0
        
        # Check detailed metrics
        detailed_metrics = service.calculate_detailed_engagement_metrics(emotion_results)
        assert "base_score" in detailed_metrics
        assert "final_score" in detailed_metrics
"""
Tests for liveness detection service.
"""

import pytest
import numpy as np
import cv2
from datetime import datetime
from unittest.mock import Mock, patch

from backend.services.liveness_detection_service import (
    LivenessDetectionService,
    EyeBlinkDetector,
    HeadMovementDetector,
    TextureAnalyzer,
    LivenessResult
)


class TestEyeBlinkDetector:
    """Test eye blink detection functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.detector = EyeBlinkDetector()
    
    def test_ear_calculation(self):
        """Test Eye Aspect Ratio calculation."""
        # Create mock eye landmarks (6 points)
        eye_landmarks = np.array([
            [100, 150],  # Left corner
            [110, 145],  # Top left
            [120, 140],  # Top right
            [130, 150],  # Right corner
            [120, 160],  # Bottom right
            [110, 165]   # Bottom left
        ])
        
        ear = self.detector.calculate_ear(eye_landmarks)
        
        assert isinstance(ear, float)
        assert 0.0 <= ear <= 1.0
    
    def test_blink_score_calculation(self):
        """Test blink score calculation."""
        # Simulate some blink history
        self.detector.blink_history.extend([False] * 20 + [True] * 5 + [False] * 20)
        self.detector.ear_history.extend([0.3] * 20 + [0.2] * 5 + [0.3] * 20)
        
        score = self.detector.get_blink_score()
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_reset_functionality(self):
        """Test detector reset."""
        # Add some data
        self.detector.blink_history.extend([True, False, True])
        self.detector.ear_history.extend([0.2, 0.3, 0.2])
        self.detector.blink_counter = 5
        
        # Reset
        self.detector.reset()
        
        assert len(self.detector.blink_history) == 0
        assert len(self.detector.ear_history) == 0
        assert self.detector.blink_counter == 0


class TestHeadMovementDetector:
    """Test head movement detection functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.detector = HeadMovementDetector()
    
    def test_head_pose_estimation(self):
        """Test head pose estimation."""
        # Create mock landmarks
        landmarks = np.array([
            [150, 200],  # Nose tip
            [120, 180],  # Left eye corner
            [180, 180],  # Right eye corner
            [130, 220],  # Left mouth corner
            [170, 220],  # Right mouth corner
            [150, 240]   # Chin
        ], dtype=np.float32)
        
        frame_shape = (480, 640)
        
        translation, rotation = self.detector.estimate_head_pose(landmarks, frame_shape)
        
        assert isinstance(translation, np.ndarray)
        assert isinstance(rotation, np.ndarray)
        assert len(translation) == 3
        assert len(rotation) == 3
    
    def test_movement_score_calculation(self):
        """Test movement score calculation."""
        # Simulate some movement history
        positions = [np.array([0, 0, 0]), np.array([1, 1, 0]), np.array([2, 0, 1])]
        rotations = [np.array([0, 0, 0]), np.array([0.1, 0, 0]), np.array([0, 0.1, 0])]
        
        self.detector.position_history.extend(positions * 10)
        self.detector.rotation_history.extend(rotations * 10)
        
        score = self.detector.get_movement_score()
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_reset_functionality(self):
        """Test detector reset."""
        # Add some data
        self.detector.position_history.extend([np.array([1, 2, 3])])
        self.detector.rotation_history.extend([np.array([0.1, 0.2, 0.3])])
        
        # Reset
        self.detector.reset()
        
        assert len(self.detector.position_history) == 0
        assert len(self.detector.rotation_history) == 0


class TestTextureAnalyzer:
    """Test texture analysis functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.analyzer = TextureAnalyzer()
    
    def test_simple_lbp_calculation(self):
        """Test simple LBP calculation."""
        # Create a simple test image
        image = np.random.randint(0, 255, (64, 64), dtype=np.uint8)
        
        lbp = self.analyzer._simple_lbp(image)
        
        assert isinstance(lbp, np.ndarray)
        assert lbp.shape == image.shape
    
    def test_texture_analysis(self):
        """Test texture analysis."""
        # Create a test face ROI
        face_roi = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        score = self.analyzer.analyze_texture(face_roi)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_texture_analysis_grayscale(self):
        """Test texture analysis with grayscale image."""
        # Create a grayscale test image
        face_roi = np.random.randint(0, 255, (100, 100), dtype=np.uint8)
        
        score = self.analyzer.analyze_texture(face_roi)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestLivenessDetectionService:
    """Test complete liveness detection service."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.service = LivenessDetectionService()
    
    def create_test_frame(self, width=640, height=480):
        """Create a test video frame."""
        return np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    
    def test_service_initialization(self):
        """Test service initialization."""
        assert self.service.blink_detector is not None
        assert self.service.movement_detector is not None
        assert self.service.texture_analyzer is not None
        assert self.service.liveness_threshold == 0.6
        assert self.service.min_analysis_frames == 30
    
    @patch('backend.services.liveness_detection_service.mp.solutions.face_detection')
    def test_extract_largest_face(self, mock_face_detection):
        """Test face extraction from frame."""
        # Mock MediaPipe face detection
        mock_detection = Mock()
        mock_detection.location_data.relative_bounding_box.xmin = 0.2
        mock_detection.location_data.relative_bounding_box.ymin = 0.2
        mock_detection.location_data.relative_bounding_box.width = 0.3
        mock_detection.location_data.relative_bounding_box.height = 0.4
        
        mock_results = Mock()
        mock_results.detections = [mock_detection]
        
        mock_face_detection_instance = Mock()
        mock_face_detection_instance.process.return_value = mock_results
        mock_face_detection.FaceDetection.return_value = mock_face_detection_instance
        
        frame = self.create_test_frame()
        face_roi = self.service._extract_largest_face(frame)
        
        # Should return a face region (or None if no face detected)
        assert face_roi is None or isinstance(face_roi, np.ndarray)
    
    def test_calculate_liveness_confidence(self):
        """Test liveness confidence calculation."""
        blink_score = 0.8
        movement_score = 0.6
        texture_score = 0.7
        
        confidence = self.service._calculate_liveness_confidence(
            blink_score, movement_score, texture_score
        )
        
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        
        # Test with extreme values
        confidence_low = self.service._calculate_liveness_confidence(0.0, 0.0, 0.0)
        confidence_high = self.service._calculate_liveness_confidence(1.0, 1.0, 1.0)
        
        assert confidence_low == 0.0
        assert confidence_high == 1.0
    
    def test_session_management(self):
        """Test session management functionality."""
        session_id = "test_session"
        
        # Test session creation
        frame = self.create_test_frame()
        result = self.service.analyze_frame(frame, session_id)
        
        assert session_id in self.service.active_sessions
        assert isinstance(result, LivenessResult)
        
        # Test session stats
        stats = self.service.get_session_stats(session_id)
        assert isinstance(stats, dict)
        assert stats['session_id'] == session_id
        assert stats['frame_count'] >= 1
        
        # Test session reset
        self.service.reset_session(session_id)
        assert session_id not in self.service.active_sessions
    
    def test_verify_liveness_insufficient_frames(self):
        """Test liveness verification with insufficient frames."""
        # Create sequence with too few frames
        face_sequence = [self.create_test_frame() for _ in range(10)]
        
        result = self.service.verify_liveness(face_sequence)
        
        # Should return False due to insufficient frames
        assert result is False
    
    def test_verify_liveness_sufficient_frames(self):
        """Test liveness verification with sufficient frames."""
        # Create sequence with enough frames
        face_sequence = [self.create_test_frame() for _ in range(35)]
        
        result = self.service.verify_liveness(face_sequence)
        
        # Should return a boolean result
        assert isinstance(result, bool)
    
    def test_get_liveness_score(self):
        """Test getting liveness score for a frame."""
        frame = self.create_test_frame()
        
        score = self.service.get_liveness_score(frame)
        
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_threshold_updates(self):
        """Test updating detection thresholds."""
        original_liveness = self.service.liveness_threshold
        original_blink = self.service.blink_detector.ear_threshold
        original_movement = self.service.movement_detector.movement_threshold
        
        # Update thresholds
        new_liveness = 0.8
        new_blink = 0.3
        new_movement = 10.0
        
        self.service.update_thresholds(
            liveness_threshold=new_liveness,
            blink_threshold=new_blink,
            movement_threshold=new_movement
        )
        
        assert self.service.liveness_threshold == new_liveness
        assert self.service.blink_detector.ear_threshold == new_blink
        assert self.service.movement_detector.movement_threshold == new_movement
    
    def test_processing_stats(self):
        """Test processing statistics tracking."""
        initial_stats = self.service.get_processing_stats()
        
        # Process a frame
        frame = self.create_test_frame()
        self.service.analyze_frame(frame)
        
        updated_stats = self.service.get_processing_stats()
        
        assert updated_stats['total_processed'] > initial_stats['total_processed']
        assert updated_stats['successful_processed'] >= initial_stats['successful_processed']


class TestLivenessResult:
    """Test LivenessResult data class."""
    
    def test_liveness_result_creation(self):
        """Test creating a LivenessResult object."""
        result = LivenessResult(
            is_live=True,
            confidence=0.85,
            blink_score=0.8,
            movement_score=0.7,
            texture_score=0.9,
            timestamp=datetime.now(),
            details={'test': 'data'}
        )
        
        assert result.is_live is True
        assert result.confidence == 0.85
        assert result.blink_score == 0.8
        assert result.movement_score == 0.7
        assert result.texture_score == 0.9
        assert isinstance(result.timestamp, datetime)
        assert result.details == {'test': 'data'}
    
    def test_liveness_result_false_case(self):
        """Test LivenessResult for non-live detection."""
        result = LivenessResult(
            is_live=False,
            confidence=0.3,
            blink_score=0.2,
            movement_score=0.1,
            texture_score=0.4,
            timestamp=datetime.now(),
            details={'reason': 'low_confidence'}
        )
        
        assert result.is_live is False
        assert result.confidence == 0.3
        assert result.details['reason'] == 'low_confidence'
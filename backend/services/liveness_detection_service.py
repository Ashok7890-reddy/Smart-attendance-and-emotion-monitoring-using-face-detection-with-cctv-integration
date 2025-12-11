"""
Liveness Detection Service for anti-spoofing.

This service implements various liveness detection techniques including
eye blink detection, head movement analysis, and texture analysis.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from datetime import datetime, timedelta
from collections import deque
import logging
from dataclasses import dataclass

from backend.core.base_service import BaseProcessingService

# Try to import MediaPipe, but provide fallback if not available
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None


@dataclass
class LivenessResult:
    """Result of liveness detection analysis."""
    is_live: bool
    confidence: float
    blink_score: float
    movement_score: float
    texture_score: float
    timestamp: datetime
    details: Dict[str, float]


class EyeBlinkDetector:
    """Eye blink detection for liveness verification."""
    
    def __init__(self):
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.mp_face_mesh = None
            self.face_mesh = None
        
        # Eye landmark indices for MediaPipe face mesh (simplified key points)
        self.left_eye_indices = [33, 7, 163, 144, 145, 153]
        self.right_eye_indices = [362, 382, 381, 380, 374, 373]
        
        # EAR (Eye Aspect Ratio) thresholds
        self.ear_threshold = 0.25
        self.consecutive_frames = 3
        self.min_blinks_required = 2
        self.analysis_window = 60  # frames
        
        # Blink tracking
        self.blink_counter = 0
        self.frame_counter = 0
        self.blink_history = deque(maxlen=self.analysis_window)
        self.ear_history = deque(maxlen=self.analysis_window)
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def calculate_ear(self, eye_landmarks: np.ndarray) -> float:
        """
        Calculate Eye Aspect Ratio (EAR).
        
        Args:
            eye_landmarks: Eye landmark coordinates (6 points)
            
        Returns:
            Eye aspect ratio
        """
        try:
            # Calculate distances between vertical eye landmarks
            A = np.linalg.norm(eye_landmarks[1] - eye_landmarks[5])
            B = np.linalg.norm(eye_landmarks[2] - eye_landmarks[4])
            
            # Calculate distance between horizontal eye landmarks
            C = np.linalg.norm(eye_landmarks[0] - eye_landmarks[3])
            
            # Calculate EAR
            ear = (A + B) / (2.0 * C + 1e-8)
            return ear
            
        except Exception as e:
            self.logger.error(f"EAR calculation failed: {e}")
            return 0.3  # Default value
    
    def detect_blink(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Detect eye blink in a frame.
        
        Args:
            frame: Input video frame
            
        Returns:
            Tuple of (blink_detected, ear_value)
        """
        try:
            if not MEDIAPIPE_AVAILABLE or self.face_mesh is None:
                # Fallback: simulate blink detection
                return self._simulate_blink_detection(frame)
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            
            if not results.multi_face_landmarks:
                return False, 0.0
            
            face_landmarks = results.multi_face_landmarks[0]
            
            # Extract eye landmarks
            h, w = frame.shape[:2]
            left_eye_coords = []
            right_eye_coords = []
            
            for idx in self.left_eye_indices:
                landmark = face_landmarks.landmark[idx]
                left_eye_coords.append([landmark.x * w, landmark.y * h])
            
            for idx in self.right_eye_indices:
                landmark = face_landmarks.landmark[idx]
                right_eye_coords.append([landmark.x * w, landmark.y * h])
            
            left_eye_coords = np.array(left_eye_coords)
            right_eye_coords = np.array(right_eye_coords)
            
            # Calculate EAR for both eyes
            left_ear = self.calculate_ear(left_eye_coords)
            right_ear = self.calculate_ear(right_eye_coords)
            
            # Average EAR
            avg_ear = (left_ear + right_ear) / 2.0
            
            # Check for blink
            blink_detected = False
            if avg_ear < self.ear_threshold:
                self.frame_counter += 1
            else:
                if self.frame_counter >= self.consecutive_frames:
                    self.blink_counter += 1
                    blink_detected = True
                self.frame_counter = 0
            
            # Update history
            self.blink_history.append(blink_detected)
            self.ear_history.append(avg_ear)
            
            return blink_detected, avg_ear
            
        except Exception as e:
            self.logger.error(f"Blink detection failed: {e}")
            return False, 0.0
    
    def get_blink_score(self) -> float:
        """
        Calculate blink score based on recent blink history.
        
        Returns:
            Blink score between 0 and 1
        """
        try:
            if len(self.blink_history) < self.analysis_window // 2:
                return 0.0
            
            # Count blinks in recent history
            recent_blinks = sum(self.blink_history)
            
            # Calculate blink rate (blinks per second, assuming 30 FPS)
            blink_rate = recent_blinks / (len(self.blink_history) / 30.0)
            
            # Normal blink rate is 0.3-0.5 blinks per second
            if 0.2 <= blink_rate <= 0.8:
                score = 1.0
            elif 0.1 <= blink_rate <= 1.0:
                score = 0.7
            else:
                score = 0.3
            
            # Check EAR variance (natural blinking has variance)
            if len(self.ear_history) > 10:
                ear_variance = np.var(list(self.ear_history))
                if ear_variance > 0.01:  # Good variance indicates natural blinking
                    score = min(score + 0.2, 1.0)
            
            return score
            
        except Exception as e:
            self.logger.error(f"Blink score calculation failed: {e}")
            return 0.0
    
    def _simulate_blink_detection(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Simulate blink detection when MediaPipe is not available.
        
        Args:
            frame: Input video frame
            
        Returns:
            Tuple of (blink_detected, ear_value)
        """
        # Simple simulation based on frame analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Use Haar cascade for face detection as fallback
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return False, 0.0
        
        # Simulate EAR calculation based on image properties
        # This is a simplified approach for demonstration
        avg_intensity = np.mean(gray)
        ear_value = 0.3 + (avg_intensity / 255.0) * 0.2  # Simulate EAR between 0.3-0.5
        
        # Simulate blink detection
        blink_detected = False
        if ear_value < self.ear_threshold:
            self.frame_counter += 1
        else:
            if self.frame_counter >= self.consecutive_frames:
                self.blink_counter += 1
                blink_detected = True
            self.frame_counter = 0
        
        # Update history
        self.blink_history.append(blink_detected)
        self.ear_history.append(ear_value)
        
        return blink_detected, ear_value
    
    def reset(self):
        """Reset blink detection state."""
        self.blink_counter = 0
        self.frame_counter = 0
        self.blink_history.clear()
        self.ear_history.clear()


class HeadMovementDetector:
    """Head movement detection for liveness verification."""
    
    def __init__(self):
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.mp_face_mesh = None
            self.face_mesh = None
        
        # Key facial landmarks for head pose estimation
        self.pose_landmarks = [1, 33, 61, 199, 263, 291]  # Nose tip, eye corners, chin
        
        # Movement tracking
        self.position_history = deque(maxlen=60)  # Track last 60 frames
        self.rotation_history = deque(maxlen=60)
        self.movement_threshold = 5.0  # pixels
        self.rotation_threshold = 2.0  # degrees
        
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def estimate_head_pose(self, landmarks: np.ndarray, frame_shape: Tuple[int, int]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Estimate head pose from facial landmarks.
        
        Args:
            landmarks: Facial landmark coordinates
            frame_shape: Frame dimensions (height, width)
            
        Returns:
            Tuple of (translation_vector, rotation_vector)
        """
        try:
            h, w = frame_shape
            
            # 3D model points (approximate face model)
            model_points = np.array([
                (0.0, 0.0, 0.0),             # Nose tip
                (-30.0, -125.0, -30.0),      # Left eye left corner
                (30.0, -125.0, -30.0),       # Right eye right corner
                (-60.0, -70.0, -60.0),       # Left Mouth corner
                (60.0, -70.0, -60.0),        # Right mouth corner
                (0.0, 110.0, -10.0)          # Chin
            ])
            
            # Camera internals (approximate)
            focal_length = w
            center = (w / 2, h / 2)
            camera_matrix = np.array([
                [focal_length, 0, center[0]],
                [0, focal_length, center[1]],
                [0, 0, 1]
            ], dtype=np.float32)
            
            # Distortion coefficients (assuming no distortion)
            dist_coeffs = np.zeros((4, 1))
            
            # Solve PnP
            success, rotation_vector, translation_vector = cv2.solvePnP(
                model_points,
                landmarks,
                camera_matrix,
                dist_coeffs
            )
            
            if success:
                return translation_vector.flatten(), rotation_vector.flatten()
            else:
                return np.zeros(3), np.zeros(3)
                
        except Exception as e:
            self.logger.error(f"Head pose estimation failed: {e}")
            return np.zeros(3), np.zeros(3)
    
    def detect_movement(self, frame: np.ndarray) -> Tuple[float, float]:
        """
        Detect head movement in a frame.
        
        Args:
            frame: Input video frame
            
        Returns:
            Tuple of (position_movement, rotation_movement)
        """
        try:
            if not MEDIAPIPE_AVAILABLE or self.face_mesh is None:
                # Fallback: simulate movement detection
                return self._simulate_movement_detection(frame)
            
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb_frame)
            
            if not results.multi_face_landmarks:
                return 0.0, 0.0
            
            face_landmarks = results.multi_face_landmarks[0]
            h, w = frame.shape[:2]
            
            # Extract key landmarks for pose estimation
            landmark_coords = []
            for idx in self.pose_landmarks:
                landmark = face_landmarks.landmark[idx]
                landmark_coords.append([landmark.x * w, landmark.y * h])
            
            landmark_coords = np.array(landmark_coords, dtype=np.float32)
            
            # Estimate head pose
            translation, rotation = self.estimate_head_pose(landmark_coords, (h, w))
            
            # Calculate movement
            position_movement = 0.0
            rotation_movement = 0.0
            
            if len(self.position_history) > 0:
                # Calculate position change
                prev_translation = self.position_history[-1]
                position_diff = np.linalg.norm(translation - prev_translation)
                position_movement = position_diff
                
                # Calculate rotation change
                prev_rotation = self.rotation_history[-1]
                rotation_diff = np.linalg.norm(rotation - prev_rotation)
                rotation_movement = np.degrees(rotation_diff)
            
            # Update history
            self.position_history.append(translation)
            self.rotation_history.append(rotation)
            
            return position_movement, rotation_movement
            
        except Exception as e:
            self.logger.error(f"Movement detection failed: {e}")
            return 0.0, 0.0
    
    def get_movement_score(self) -> float:
        """
        Calculate movement score based on recent movement history.
        
        Returns:
            Movement score between 0 and 1
        """
        try:
            if len(self.position_history) < 30:
                return 0.0
            
            # Calculate movement statistics
            positions = np.array(list(self.position_history))
            rotations = np.array(list(self.rotation_history))
            
            # Calculate variance in position and rotation
            position_variance = np.var(positions, axis=0)
            rotation_variance = np.var(rotations, axis=0)
            
            # Score based on natural head movement
            position_score = 0.0
            if np.mean(position_variance) > 10:  # Some movement detected
                position_score = 0.5
            if np.mean(position_variance) > 50:  # Good amount of movement
                position_score = 1.0
            
            rotation_score = 0.0
            if np.mean(rotation_variance) > 0.1:  # Some rotation detected
                rotation_score = 0.5
            if np.mean(rotation_variance) > 0.5:  # Good amount of rotation
                rotation_score = 1.0
            
            # Combined score
            movement_score = (position_score + rotation_score) / 2.0
            
            return movement_score
            
        except Exception as e:
            self.logger.error(f"Movement score calculation failed: {e}")
            return 0.0
    
    def _simulate_movement_detection(self, frame: np.ndarray) -> Tuple[float, float]:
        """
        Simulate movement detection when MediaPipe is not available.
        
        Args:
            frame: Input video frame
            
        Returns:
            Tuple of (position_movement, rotation_movement)
        """
        # Simple simulation based on frame analysis
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Use Haar cascade for face detection as fallback
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return 0.0, 0.0
        
        # Get the largest face
        largest_face = max(faces, key=lambda x: x[2] * x[3])
        x, y, w, h = largest_face
        
        # Calculate face center
        face_center = np.array([x + w/2, y + h/2, 0])
        
        # Simulate rotation based on face aspect ratio
        aspect_ratio = w / h
        rotation = np.array([0, 0, aspect_ratio - 1.0])
        
        # Calculate movement
        position_movement = 0.0
        rotation_movement = 0.0
        
        if len(self.position_history) > 0:
            # Calculate position change
            prev_translation = self.position_history[-1]
            position_diff = np.linalg.norm(face_center - prev_translation)
            position_movement = position_diff
            
            # Calculate rotation change
            prev_rotation = self.rotation_history[-1]
            rotation_diff = np.linalg.norm(rotation - prev_rotation)
            rotation_movement = rotation_diff
        
        # Update history
        self.position_history.append(face_center)
        self.rotation_history.append(rotation)
        
        return position_movement, rotation_movement
    
    def reset(self):
        """Reset movement detection state."""
        self.position_history.clear()
        self.rotation_history.clear()


class TextureAnalyzer:
    """Texture analysis for photo/video spoof detection."""
    
    def __init__(self):
        self.lbp_radius = 1
        self.lbp_n_points = 8
        self.texture_threshold = 0.5
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def calculate_lbp(self, image: np.ndarray) -> np.ndarray:
        """
        Calculate Local Binary Pattern (LBP) for texture analysis.
        
        Args:
            image: Grayscale input image
            
        Returns:
            LBP image
        """
        try:
            from skimage.feature import local_binary_pattern
            
            # Calculate LBP
            lbp = local_binary_pattern(
                image,
                self.lbp_n_points,
                self.lbp_radius,
                method='uniform'
            )
            
            return lbp
            
        except ImportError:
            # Fallback implementation without scikit-image
            return self._simple_lbp(image)
        except Exception as e:
            self.logger.error(f"LBP calculation failed: {e}")
            return image
    
    def _simple_lbp(self, image: np.ndarray) -> np.ndarray:
        """
        Simple LBP implementation without external dependencies.
        
        Args:
            image: Grayscale input image
            
        Returns:
            LBP-like texture image
        """
        try:
            # Simple texture analysis using gradients
            grad_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
            grad_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
            
            # Calculate gradient magnitude
            gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
            
            return gradient_magnitude.astype(np.uint8)
            
        except Exception as e:
            self.logger.error(f"Simple LBP calculation failed: {e}")
            return image
    
    def analyze_texture(self, face_roi: np.ndarray) -> float:
        """
        Analyze face texture to detect photo/video spoofing.
        
        Args:
            face_roi: Face region of interest
            
        Returns:
            Texture score between 0 and 1 (higher = more likely to be live)
        """
        try:
            # Convert to grayscale if needed
            if len(face_roi.shape) == 3:
                gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            else:
                gray = face_roi
            
            # Resize for consistent analysis
            gray = cv2.resize(gray, (64, 64))
            
            # Calculate texture features
            texture_score = 0.0
            
            # 1. LBP texture analysis
            lbp = self.calculate_lbp(gray)
            lbp_variance = np.var(lbp)
            
            # Live faces have more texture variance
            if lbp_variance > 100:
                texture_score += 0.3
            elif lbp_variance > 50:
                texture_score += 0.2
            
            # 2. Edge density analysis
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / edges.size
            
            # Live faces have moderate edge density
            if 0.05 <= edge_density <= 0.3:
                texture_score += 0.3
            elif 0.02 <= edge_density <= 0.5:
                texture_score += 0.2
            
            # 3. Frequency domain analysis
            f_transform = np.fft.fft2(gray)
            f_shift = np.fft.fftshift(f_transform)
            magnitude_spectrum = np.log(np.abs(f_shift) + 1)
            
            # Calculate high frequency content
            h, w = magnitude_spectrum.shape
            center_h, center_w = h // 2, w // 2
            high_freq_region = magnitude_spectrum[
                center_h - h//4:center_h + h//4,
                center_w - w//4:center_w + w//4
            ]
            high_freq_energy = np.mean(high_freq_region)
            
            # Live faces have more high frequency content
            if high_freq_energy > 5:
                texture_score += 0.2
            elif high_freq_energy > 3:
                texture_score += 0.1
            
            # 4. Contrast analysis
            contrast = np.std(gray)
            if contrast > 30:
                texture_score += 0.2
            elif contrast > 20:
                texture_score += 0.1
            
            return min(texture_score, 1.0)
            
        except Exception as e:
            self.logger.error(f"Texture analysis failed: {e}")
            return 0.5  # Neutral score on failure


class LivenessDetectionService(BaseProcessingService):
    """Complete liveness detection service for anti-spoofing."""
    
    def __init__(self, config=None):
        super().__init__(config)
        
        # Initialize detectors
        self.blink_detector = EyeBlinkDetector()
        self.movement_detector = HeadMovementDetector()
        self.texture_analyzer = TextureAnalyzer()
        
        # Liveness thresholds
        self.liveness_threshold = 0.6
        self.min_analysis_frames = 30
        
        # Session tracking
        self.active_sessions = {}
        
        self.logger.info("Liveness detection service initialized")
    
    def analyze_frame(self, frame: np.ndarray, session_id: str = "default") -> LivenessResult:
        """
        Analyze a single frame for liveness indicators.
        
        Args:
            frame: Input video frame
            session_id: Session identifier for tracking
            
        Returns:
            LivenessResult with analysis details
        """
        try:
            # Initialize session if needed
            if session_id not in self.active_sessions:
                self.active_sessions[session_id] = {
                    'frame_count': 0,
                    'start_time': datetime.now()
                }
            
            session = self.active_sessions[session_id]
            session['frame_count'] += 1
            
            # Detect eye blinks
            blink_detected, ear_value = self.blink_detector.detect_blink(frame)
            
            # Detect head movement
            position_movement, rotation_movement = self.movement_detector.detect_movement(frame)
            
            # Extract face region for texture analysis
            face_roi = self._extract_largest_face(frame)
            texture_score = 0.5  # Default score
            if face_roi is not None:
                texture_score = self.texture_analyzer.analyze_texture(face_roi)
            
            # Calculate individual scores
            blink_score = self.blink_detector.get_blink_score()
            movement_score = self.movement_detector.get_movement_score()
            
            # Calculate overall liveness confidence
            confidence = self._calculate_liveness_confidence(
                blink_score, movement_score, texture_score
            )
            
            # Determine if face is live
            is_live = confidence >= self.liveness_threshold
            
            # Create result
            result = LivenessResult(
                is_live=is_live,
                confidence=confidence,
                blink_score=blink_score,
                movement_score=movement_score,
                texture_score=texture_score,
                timestamp=datetime.now(),
                details={
                    'ear_value': ear_value,
                    'position_movement': position_movement,
                    'rotation_movement': rotation_movement,
                    'blink_detected': blink_detected,
                    'frame_count': session['frame_count']
                }
            )
            
            self._update_stats(success=True)
            return result
            
        except Exception as e:
            self.logger.error(f"Frame analysis failed: {e}")
            self._update_stats(success=False)
            
            # Return failed result
            return LivenessResult(
                is_live=False,
                confidence=0.0,
                blink_score=0.0,
                movement_score=0.0,
                texture_score=0.0,
                timestamp=datetime.now(),
                details={'error': str(e)}
            )
    
    def verify_liveness(self, face_sequence: List[np.ndarray], session_id: str = "default") -> bool:
        """
        Verify liveness from a sequence of face images.
        
        Args:
            face_sequence: List of face images/frames
            session_id: Session identifier
            
        Returns:
            True if face is determined to be live
        """
        try:
            if len(face_sequence) < self.min_analysis_frames:
                self.logger.warning(f"Insufficient frames for liveness analysis: {len(face_sequence)}")
                return False
            
            # Reset detectors for new sequence
            self.blink_detector.reset()
            self.movement_detector.reset()
            
            results = []
            
            # Analyze each frame in sequence
            for frame in face_sequence:
                result = self.analyze_frame(frame, session_id)
                results.append(result)
            
            # Calculate final liveness decision
            if not results:
                return False
            
            # Average confidence across all frames
            avg_confidence = np.mean([r.confidence for r in results])
            
            # Check for consistent liveness indicators
            live_frames = sum(1 for r in results if r.is_live)
            live_ratio = live_frames / len(results)
            
            # Require majority of frames to indicate liveness
            final_decision = avg_confidence >= self.liveness_threshold and live_ratio >= 0.6
            
            self.logger.info(f"Liveness verification: {final_decision} (confidence: {avg_confidence:.3f}, live_ratio: {live_ratio:.3f})")
            
            return final_decision
            
        except Exception as e:
            self.logger.error(f"Liveness verification failed: {e}")
            return False
    
    def get_liveness_score(self, frame: np.ndarray, session_id: str = "default") -> float:
        """
        Get liveness score for a single frame.
        
        Args:
            frame: Input video frame
            session_id: Session identifier
            
        Returns:
            Liveness score between 0 and 1
        """
        try:
            result = self.analyze_frame(frame, session_id)
            return result.confidence
            
        except Exception as e:
            self.logger.error(f"Liveness score calculation failed: {e}")
            return 0.0
    
    def _extract_largest_face(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract the largest face region from frame.
        
        Args:
            frame: Input video frame
            
        Returns:
            Face region of interest or None
        """
        try:
            if MEDIAPIPE_AVAILABLE:
                # Use MediaPipe face detection
                mp_face_detection = mp.solutions.face_detection
                face_detection = mp_face_detection.FaceDetection(
                    model_selection=1,
                    min_detection_confidence=0.5
                )
                
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_detection.process(rgb_frame)
                
                if not results.detections:
                    return None
                
                # Find largest face
                largest_face = None
                largest_area = 0
                
                h, w = frame.shape[:2]
                
                for detection in results.detections:
                    bbox = detection.location_data.relative_bounding_box
                    
                    # Convert to absolute coordinates
                    x = int(bbox.xmin * w)
                    y = int(bbox.ymin * h)
                    width = int(bbox.width * w)
                    height = int(bbox.height * h)
                    
                    area = width * height
                    
                    if area > largest_area:
                        largest_area = area
                        # Extract face ROI with padding
                        pad = 20
                        x1 = max(0, x - pad)
                        y1 = max(0, y - pad)
                        x2 = min(w, x + width + pad)
                        y2 = min(h, y + height + pad)
                        
                        largest_face = frame[y1:y2, x1:x2]
                
                return largest_face
            else:
                # Fallback: use OpenCV Haar cascade
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                
                if len(faces) == 0:
                    return None
                
                # Get the largest face
                largest_face_coords = max(faces, key=lambda x: x[2] * x[3])
                x, y, w, h = largest_face_coords
                
                # Extract face ROI with padding
                pad = 20
                x1 = max(0, x - pad)
                y1 = max(0, y - pad)
                x2 = min(frame.shape[1], x + w + pad)
                y2 = min(frame.shape[0], y + h + pad)
                
                return frame[y1:y2, x1:x2]
            
        except Exception as e:
            self.logger.error(f"Face extraction failed: {e}")
            return None
    
    def _calculate_liveness_confidence(self, blink_score: float, movement_score: float, texture_score: float) -> float:
        """
        Calculate overall liveness confidence from individual scores.
        
        Args:
            blink_score: Eye blink analysis score
            movement_score: Head movement analysis score
            texture_score: Texture analysis score
            
        Returns:
            Overall confidence score between 0 and 1
        """
        try:
            # Weighted combination of scores
            weights = {
                'blink': 0.4,
                'movement': 0.3,
                'texture': 0.3
            }
            
            confidence = (
                weights['blink'] * blink_score +
                weights['movement'] * movement_score +
                weights['texture'] * texture_score
            )
            
            return min(max(confidence, 0.0), 1.0)
            
        except Exception as e:
            self.logger.error(f"Confidence calculation failed: {e}")
            return 0.0
    
    def reset_session(self, session_id: str = "default"):
        """
        Reset liveness detection session.
        
        Args:
            session_id: Session identifier to reset
        """
        try:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            self.blink_detector.reset()
            self.movement_detector.reset()
            
            self.logger.info(f"Session {session_id} reset")
            
        except Exception as e:
            self.logger.error(f"Session reset failed: {e}")
    
    def get_session_stats(self, session_id: str = "default") -> Dict:
        """
        Get statistics for a liveness detection session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session statistics dictionary
        """
        try:
            if session_id not in self.active_sessions:
                return {}
            
            session = self.active_sessions[session_id]
            
            stats = {
                'session_id': session_id,
                'frame_count': session['frame_count'],
                'start_time': session['start_time'],
                'duration': (datetime.now() - session['start_time']).total_seconds(),
                'blink_count': self.blink_detector.blink_counter,
                'processing_stats': self.get_processing_stats()
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Session stats retrieval failed: {e}")
            return {}
    
    def update_thresholds(self, liveness_threshold: Optional[float] = None, 
                         blink_threshold: Optional[float] = None,
                         movement_threshold: Optional[float] = None):
        """
        Update detection thresholds.
        
        Args:
            liveness_threshold: Overall liveness threshold
            blink_threshold: Eye blink detection threshold
            movement_threshold: Head movement detection threshold
        """
        try:
            if liveness_threshold is not None:
                self.liveness_threshold = liveness_threshold
                self.logger.info(f"Liveness threshold updated to {liveness_threshold}")
            
            if blink_threshold is not None:
                self.blink_detector.ear_threshold = blink_threshold
                self.logger.info(f"Blink threshold updated to {blink_threshold}")
            
            if movement_threshold is not None:
                self.movement_detector.movement_threshold = movement_threshold
                self.logger.info(f"Movement threshold updated to {movement_threshold}")
                
        except Exception as e:
            self.logger.error(f"Threshold update failed: {e}")
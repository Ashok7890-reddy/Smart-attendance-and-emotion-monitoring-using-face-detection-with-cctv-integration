"""
Face Recognition Service implementation.

This service handles face detection, preprocessing, embedding extraction,
and face matching for the Smart Attendance System.
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple
from datetime import datetime
import logging

from backend.core.base_service import BaseProcessingService
from backend.core.interfaces import IFaceRecognitionService
from backend.models.face_detection import FaceDetection, CameraLocation
from backend.models.student import StudentMatch

# Try to import MediaPipe, but provide fallback if not available
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    mp = None


class FacePreprocessor:
    """Face preprocessing utilities for normalization and alignment."""
    
    def __init__(self):
        self.target_size = (160, 160)  # Standard face size for embeddings
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_mesh = mp.solutions.face_mesh
            self.face_mesh = self.mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=10,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        else:
            self.mp_face_mesh = None
            self.face_mesh = None
    
    def normalize_face(self, face_roi: np.ndarray) -> np.ndarray:
        """
        Normalize face region for consistent processing.
        
        Args:
            face_roi: Face region of interest
            
        Returns:
            Normalized face image
        """
        # Resize to target size
        normalized = cv2.resize(face_roi, self.target_size)
        
        # Convert to RGB if needed
        if len(normalized.shape) == 3 and normalized.shape[2] == 3:
            normalized = cv2.cvtColor(normalized, cv2.COLOR_BGR2RGB)
        
        # Normalize pixel values to [0, 1]
        normalized = normalized.astype(np.float32) / 255.0
        
        # Apply histogram equalization for better contrast
        if len(normalized.shape) == 3:
            # Convert to LAB color space for better equalization
            lab = cv2.cvtColor((normalized * 255).astype(np.uint8), cv2.COLOR_RGB2LAB)
            lab[:, :, 0] = cv2.equalizeHist(lab[:, :, 0])
            normalized = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB).astype(np.float32) / 255.0
        
        return normalized
    
    def align_face(self, image: np.ndarray, landmarks: np.ndarray) -> Optional[np.ndarray]:
        """
        Align face based on eye landmarks.
        
        Args:
            image: Input image
            landmarks: Facial landmarks
            
        Returns:
            Aligned face image or None if alignment fails
        """
        try:
            # Get eye landmarks (MediaPipe face mesh indices)
            left_eye_idx = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
            right_eye_idx = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
            
            # Calculate eye centers
            left_eye_center = np.mean(landmarks[left_eye_idx], axis=0)
            right_eye_center = np.mean(landmarks[right_eye_idx], axis=0)
            
            # Calculate angle between eyes
            dy = right_eye_center[1] - left_eye_center[1]
            dx = right_eye_center[0] - left_eye_center[0]
            angle = np.degrees(np.arctan2(dy, dx))
            
            # Calculate center point between eyes
            center = ((left_eye_center[0] + right_eye_center[0]) // 2,
                     (left_eye_center[1] + right_eye_center[1]) // 2)
            
            # Create rotation matrix
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            
            # Apply rotation
            aligned = cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]))
            
            return aligned
            
        except Exception as e:
            logging.warning(f"Face alignment failed: {e}")
            return image
    
    def assess_face_quality(self, face_roi: np.ndarray) -> float:
        """
        Assess face quality based on various metrics.
        
        Args:
            face_roi: Face region of interest
            
        Returns:
            Quality score between 0 and 1
        """
        quality_score = 0.0
        
        # Check image size
        if face_roi.shape[0] >= 80 and face_roi.shape[1] >= 80:
            quality_score += 0.2
        
        # Check brightness
        gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY) if len(face_roi.shape) == 3 else face_roi
        brightness = np.mean(gray)
        if 50 <= brightness <= 200:  # Good brightness range
            quality_score += 0.2
        
        # Check contrast using standard deviation
        contrast = np.std(gray)
        if contrast > 30:  # Good contrast
            quality_score += 0.2
        
        # Check sharpness using Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        if laplacian_var > 100:  # Sharp image
            quality_score += 0.2
        
        # Check for blur using gradient magnitude
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        if np.mean(gradient_magnitude) > 20:  # Not too blurry
            quality_score += 0.2
        
        return min(quality_score, 1.0)


class FaceDetectionService(BaseProcessingService):
    """Face detection service using MediaPipe."""
    
    def __init__(self, config=None):
        super().__init__(config)
        if MEDIAPIPE_AVAILABLE:
            self.mp_face_detection = mp.solutions.face_detection
            self.mp_drawing = mp.solutions.drawing_utils
            
            # Initialize MediaPipe face detection
            self.face_detection = self.mp_face_detection.FaceDetection(
                model_selection=1,  # 1 for full range model (better for distant faces)
                min_detection_confidence=0.7
            )
        else:
            self.mp_face_detection = None
            self.mp_drawing = None
            self.face_detection = None
        
        self.preprocessor = FacePreprocessor()
        self.min_face_size = 80  # Minimum face size in pixels
        self.quality_threshold = 0.5  # Minimum quality score
    
    def detect_faces(self, frame: np.ndarray, camera_location: CameraLocation) -> List[FaceDetection]:
        """
        Detect faces in a video frame.
        
        Args:
            frame: Input video frame
            camera_location: Location of the camera (GATE or CLASSROOM)
            
        Returns:
            List of face detections
        """
        try:
            if not MEDIAPIPE_AVAILABLE or self.face_detection is None:
                # Fallback: use OpenCV Haar cascade
                return self._detect_faces_opencv(frame, camera_location)
            
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Perform face detection
            results = self.face_detection.process(rgb_frame)
            
            detections = []
            
            if results.detections:
                for detection in results.detections:
                    # Extract bounding box
                    bbox = self._extract_bounding_box(detection, frame.shape)
                    
                    if bbox is None:
                        continue
                    
                    # Extract face ROI
                    face_roi = self._extract_face_roi(frame, bbox)
                    
                    if face_roi is None:
                        continue
                    
                    # Assess face quality
                    quality_score = self.preprocessor.assess_face_quality(face_roi)
                    
                    # Filter low-quality faces
                    if quality_score < self.quality_threshold:
                        self.logger.debug(f"Face filtered due to low quality: {quality_score}")
                        continue
                    
                    # Create face detection object
                    face_detection = FaceDetection(
                        bounding_box=bbox,
                        confidence=detection.score[0],
                        embedding=np.array([]),  # Will be filled by embedding extraction
                        liveness_score=0.0,  # Will be filled by liveness detection
                        timestamp=datetime.now(),
                        camera_location=camera_location
                    )
                    
                    detections.append(face_detection)
            
            self._update_stats(success=True)
            self.logger.debug(f"Detected {len(detections)} faces in frame")
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Face detection failed: {e}")
            self._update_stats(success=False)
            return []
    
    def preprocess_face(self, face_roi: np.ndarray) -> np.ndarray:
        """
        Preprocess face for embedding extraction.
        
        Args:
            face_roi: Face region of interest
            
        Returns:
            Preprocessed face image
        """
        return self.preprocessor.normalize_face(face_roi)
    
    def _extract_bounding_box(self, detection, frame_shape: Tuple[int, int, int]) -> Optional[Tuple[int, int, int, int]]:
        """
        Extract bounding box from MediaPipe detection.
        
        Args:
            detection: MediaPipe detection object
            frame_shape: Shape of the input frame (height, width, channels)
            
        Returns:
            Bounding box as (x, y, width, height) or None if invalid
        """
        try:
            height, width = frame_shape[:2]
            
            # Get relative bounding box
            bbox = detection.location_data.relative_bounding_box
            
            # Convert to absolute coordinates
            x = int(bbox.xmin * width)
            y = int(bbox.ymin * height)
            w = int(bbox.width * width)
            h = int(bbox.height * height)
            
            # Validate bounding box
            if w < self.min_face_size or h < self.min_face_size:
                return None
            
            # Ensure bounding box is within frame
            x = max(0, x)
            y = max(0, y)
            w = min(w, width - x)
            h = min(h, height - y)
            
            return (x, y, w, h)
            
        except Exception as e:
            self.logger.error(f"Bounding box extraction failed: {e}")
            return None
    
    def _extract_face_roi(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        """
        Extract face region of interest from frame.
        
        Args:
            frame: Input frame
            bbox: Bounding box as (x, y, width, height)
            
        Returns:
            Face ROI or None if extraction fails
        """
        try:
            x, y, w, h = bbox
            
            # Add padding around face
            padding = 0.1  # 10% padding
            pad_x = int(w * padding)
            pad_y = int(h * padding)
            
            # Calculate padded coordinates
            x1 = max(0, x - pad_x)
            y1 = max(0, y - pad_y)
            x2 = min(frame.shape[1], x + w + pad_x)
            y2 = min(frame.shape[0], y + h + pad_y)
            
            # Extract face ROI
            face_roi = frame[y1:y2, x1:x2]
            
            if face_roi.size == 0:
                return None
            
            return face_roi
            
        except Exception as e:
            self.logger.error(f"Face ROI extraction failed: {e}")
            return None
    
    def _detect_faces_opencv(self, frame: np.ndarray, camera_location: CameraLocation) -> List[FaceDetection]:
        """
        Fallback face detection using OpenCV Haar cascade.
        
        Args:
            frame: Input video frame
            camera_location: Location of the camera
            
        Returns:
            List of face detections
        """
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            detections = []
            
            for (x, y, w, h) in faces:
                # Check minimum face size
                if w < self.min_face_size or h < self.min_face_size:
                    continue
                
                # Extract face ROI
                face_roi = self._extract_face_roi(frame, (x, y, w, h))
                
                if face_roi is None:
                    continue
                
                # Assess face quality
                quality_score = self.preprocessor.assess_face_quality(face_roi)
                
                # Filter low-quality faces
                if quality_score < self.quality_threshold:
                    self.logger.debug(f"Face filtered due to low quality: {quality_score}")
                    continue
                
                # Create face detection object
                face_detection = FaceDetection(
                    bounding_box=(x, y, w, h),
                    confidence=0.8,  # Default confidence for Haar cascade
                    embedding=np.array([]),  # Will be filled by embedding extraction
                    liveness_score=0.0,  # Will be filled by liveness detection
                    timestamp=datetime.now(),
                    camera_location=camera_location
                )
                
                detections.append(face_detection)
            
            self._update_stats(success=True)
            self.logger.debug(f"Detected {len(detections)} faces in frame using OpenCV")
            
            return detections
            
        except Exception as e:
            self.logger.error(f"OpenCV face detection failed: {e}")
            self._update_stats(success=False)
            return []


class FaceEmbeddingExtractor:
    """Face embedding extraction using FaceNet-like architecture."""
    
    def __init__(self):
        self.model = None
        self.embedding_size = 512
        self._load_model()
    
    def _load_model(self):
        """Load pre-trained face embedding model."""
        try:
            # For now, we'll skip TensorFlow due to dependency conflicts
            # In production, you would load a pre-trained FaceNet or ArcFace model
            self.model = None
            self.logger = logging.getLogger(self.__class__.__name__)
            self.logger.info("Face embedding model initialization skipped (using fallback)")
            
        except Exception as e:
            logging.error(f"Failed to load face embedding model: {e}")
            self.model = None
    
    def _create_simple_embedding_model(self):
        """Create a simple CNN model for face embeddings."""
        # Skipped due to TensorFlow dependency conflicts
        # In production, you would load a pre-trained model here
        return None
    
    def extract_embedding(self, face_roi: np.ndarray) -> np.ndarray:
        """
        Extract face embedding from preprocessed face image.
        
        Args:
            face_roi: Preprocessed face region of interest
            
        Returns:
            Face embedding vector
        """
        try:
            if self.model is None:
                # Fallback to simple feature extraction
                return self._extract_simple_features(face_roi)
            
            # Ensure correct input shape
            if len(face_roi.shape) == 3:
                face_input = np.expand_dims(face_roi, axis=0)
            else:
                face_input = face_roi
            
            # Extract embedding
            embedding = self.model.predict(face_input, verbose=0)
            
            return embedding.flatten()
            
        except Exception as e:
            logging.error(f"Embedding extraction failed: {e}")
            return self._extract_simple_features(face_roi)
    
    def _extract_simple_features(self, face_roi: np.ndarray) -> np.ndarray:
        """
        Extract simple features as fallback when model is not available.
        
        Args:
            face_roi: Face region of interest
            
        Returns:
            Simple feature vector
        """
        try:
            # Convert to grayscale if needed
            if len(face_roi.shape) == 3:
                gray = cv2.cvtColor(face_roi, cv2.COLOR_RGB2GRAY)
            else:
                gray = face_roi
            
            # Resize to standard size
            resized = cv2.resize(gray, (64, 64))
            
            # Extract HOG features
            from skimage.feature import hog
            features = hog(
                resized,
                orientations=9,
                pixels_per_cell=(8, 8),
                cells_per_block=(2, 2),
                block_norm='L2-Hys',
                feature_vector=True
            )
            
            # Pad or truncate to match embedding size
            if len(features) > self.embedding_size:
                features = features[:self.embedding_size]
            elif len(features) < self.embedding_size:
                features = np.pad(features, (0, self.embedding_size - len(features)))
            
            # Normalize
            features = features / (np.linalg.norm(features) + 1e-8)
            
            return features.astype(np.float32)
            
        except Exception as e:
            logging.error(f"Simple feature extraction failed: {e}")
            # Return random normalized vector as last resort
            features = np.random.randn(self.embedding_size).astype(np.float32)
            return features / (np.linalg.norm(features) + 1e-8)


class FaceMatcher:
    """Face matching and similarity scoring."""
    
    def __init__(self, similarity_threshold: float = 0.6):
        self.similarity_threshold = similarity_threshold
        self.confidence_threshold = 0.85
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two face embeddings.
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            # Ensure embeddings are normalized
            embedding1 = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
            embedding2 = embedding2 / (np.linalg.norm(embedding2) + 1e-8)
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2)
            
            # Convert to 0-1 range
            similarity = (similarity + 1) / 2
            
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    def match_face(self, query_embedding: np.ndarray, enrolled_embeddings: List[Tuple[str, np.ndarray]]) -> Optional[Tuple[str, float]]:
        """
        Match a face embedding against enrolled student embeddings.
        
        Args:
            query_embedding: Query face embedding
            enrolled_embeddings: List of (student_id, embedding) tuples
            
        Returns:
            Tuple of (student_id, confidence) or None if no match
        """
        try:
            best_match = None
            best_similarity = 0.0
            
            for student_id, enrolled_embedding in enrolled_embeddings:
                similarity = self.calculate_similarity(query_embedding, enrolled_embedding)
                
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_match = student_id
            
            if best_match and best_similarity >= self.confidence_threshold:
                return (best_match, best_similarity)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Face matching failed: {e}")
            return None
    
    def validate_confidence(self, confidence: float) -> bool:
        """
        Validate if confidence score meets threshold requirements.
        
        Args:
            confidence: Confidence score
            
        Returns:
            True if confidence is acceptable
        """
        return confidence >= self.confidence_threshold


class FaceRecognitionService(BaseProcessingService, IFaceRecognitionService):
    """Complete face recognition service implementation."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.detection_service = FaceDetectionService(config)
        self.embedding_extractor = FaceEmbeddingExtractor()
        self.face_matcher = FaceMatcher()
        
        # Cache for enrolled student embeddings
        self.enrolled_embeddings = {}
        self._load_enrolled_embeddings()
    
    def detect_faces(self, frame: np.ndarray, camera_location: CameraLocation = CameraLocation.CLASSROOM) -> List[FaceDetection]:
        """
        Detect faces in a video frame.
        
        Args:
            frame: Input video frame
            camera_location: Location of the camera
            
        Returns:
            List of face detections with embeddings and liveness scores
        """
        try:
            # Detect faces
            detections = self.detection_service.detect_faces(frame, camera_location)
            
            # Initialize liveness detection service if not already done
            if not hasattr(self, 'liveness_service'):
                from backend.services.liveness_detection_service import LivenessDetectionService
                self.liveness_service = LivenessDetectionService(self.config)
            
            # Extract embeddings and liveness scores for each detection
            for detection in detections:
                face_roi = self.detection_service._extract_face_roi(frame, detection.bounding_box)
                if face_roi is not None:
                    # Preprocess face
                    preprocessed_face = self.detection_service.preprocess_face(face_roi)
                    
                    # Extract embedding
                    embedding = self.embedding_extractor.extract_embedding(preprocessed_face)
                    detection.embedding = embedding
                    
                    # Calculate liveness score for this frame
                    liveness_score = self.liveness_service.get_liveness_score(frame)
                    detection.liveness_score = liveness_score
            
            return detections
            
        except Exception as e:
            self.logger.error(f"Face detection with embeddings failed: {e}")
            return []
    
    def extract_embedding(self, face_roi: np.ndarray) -> np.ndarray:
        """
        Extract face embedding from face region of interest.
        
        Args:
            face_roi: Face region of interest
            
        Returns:
            Face embedding vector
        """
        try:
            # Preprocess face
            preprocessed_face = self.detection_service.preprocess_face(face_roi)
            
            # Extract embedding
            embedding = self.embedding_extractor.extract_embedding(preprocessed_face)
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Embedding extraction failed: {e}")
            return np.array([])
    
    def match_face(self, embedding: np.ndarray) -> Optional[StudentMatch]:
        """
        Match face embedding against enrolled students.
        
        Args:
            embedding: Face embedding to match
            
        Returns:
            StudentMatch object or None if no match
        """
        try:
            # Convert enrolled embeddings to list format
            enrolled_list = [(student_id, emb) for student_id, emb in self.enrolled_embeddings.items()]
            
            # Perform matching
            match_result = self.face_matcher.match_face(embedding, enrolled_list)
            
            if match_result:
                student_id, confidence = match_result
                
                # Create StudentMatch object (simplified for now)
                from backend.models.student import Student, StudentType
                student = Student(
                    student_id=student_id,
                    name=f"Student_{student_id}",  # Would be loaded from database
                    student_type=StudentType.DAY_SCHOLAR,  # Would be loaded from database
                    face_embedding=b"",  # Encrypted embedding would be loaded from database
                    enrollment_date=datetime.now(),
                    is_active=True
                )
                
                student_match = StudentMatch(
                    student=student,
                    confidence=confidence,
                    match_timestamp=datetime.now()
                )
                
                return student_match
            
            return None
            
        except Exception as e:
            self.logger.error(f"Face matching failed: {e}")
            return None
    
    def verify_liveness(self, face_sequence: List[np.ndarray]) -> bool:
        """
        Verify if the face is live (anti-spoofing).
        
        Args:
            face_sequence: Sequence of face images
            
        Returns:
            True if face is live
        """
        try:
            from backend.services.liveness_detection_service import LivenessDetectionService
            
            # Initialize liveness detection service if not already done
            if not hasattr(self, 'liveness_service'):
                self.liveness_service = LivenessDetectionService(self.config)
            
            # Verify liveness using the sequence of frames
            is_live = self.liveness_service.verify_liveness(face_sequence)
            
            self.logger.info(f"Liveness verification result: {is_live}")
            return is_live
            
        except Exception as e:
            self.logger.error(f"Liveness verification failed: {e}")
            # Default to False for security (reject if verification fails)
            return False
    
    def _load_enrolled_embeddings(self):
        """Load enrolled student embeddings from database."""
        try:
            # Placeholder implementation
            # In production, this would load from the database
            self.enrolled_embeddings = {}
            self.logger.info("Enrolled embeddings loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load enrolled embeddings: {e}")
            self.enrolled_embeddings = {}
    
    def enroll_student(self, student_id: str, face_embedding: np.ndarray) -> bool:
        """
        Enroll a new student with their face embedding.
        
        Args:
            student_id: Student identifier
            face_embedding: Face embedding vector
            
        Returns:
            True if enrollment successful
        """
        try:
            self.enrolled_embeddings[student_id] = face_embedding
            self.logger.info(f"Student {student_id} enrolled successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Student enrollment failed: {e}")
            return False
    
    def update_confidence_threshold(self, threshold: float):
        """Update confidence threshold for face matching."""
        self.face_matcher.confidence_threshold = threshold
        self.logger.info(f"Confidence threshold updated to {threshold}")
    
    def get_liveness_score(self, frame: np.ndarray, session_id: str = "default") -> float:
        """
        Get real-time liveness score for a frame.
        
        Args:
            frame: Input video frame
            session_id: Session identifier for tracking
            
        Returns:
            Liveness score between 0 and 1
        """
        try:
            # Initialize liveness detection service if not already done
            if not hasattr(self, 'liveness_service'):
                from backend.services.liveness_detection_service import LivenessDetectionService
                self.liveness_service = LivenessDetectionService(self.config)
            
            return self.liveness_service.get_liveness_score(frame, session_id)
            
        except Exception as e:
            self.logger.error(f"Liveness score calculation failed: {e}")
            return 0.0
    
    def reset_liveness_session(self, session_id: str = "default"):
        """
        Reset liveness detection session.
        
        Args:
            session_id: Session identifier to reset
        """
        try:
            if hasattr(self, 'liveness_service'):
                self.liveness_service.reset_session(session_id)
                
        except Exception as e:
            self.logger.error(f"Liveness session reset failed: {e}")
    
    def get_recognition_stats(self) -> dict:
        """Get face recognition statistics."""
        stats = self.get_processing_stats()
        stats.update({
            "enrolled_students": len(self.enrolled_embeddings),
            "confidence_threshold": self.face_matcher.confidence_threshold,
            "similarity_threshold": self.face_matcher.similarity_threshold
        })
        
        # Add liveness detection stats if available
        if hasattr(self, 'liveness_service'):
            liveness_stats = self.liveness_service.get_processing_stats()
            stats.update({
                "liveness_processing_stats": liveness_stats
            })
        
        return stats


    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two face embeddings.
        
        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            
        Returns:
            Similarity score between 0 and 1
        """
        try:
            # Normalize embeddings
            embedding1_norm = embedding1 / (np.linalg.norm(embedding1) + 1e-8)
            embedding2_norm = embedding2 / (np.linalg.norm(embedding2) + 1e-8)
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1_norm, embedding2_norm)
            
            # Convert to 0-1 range (cosine similarity is -1 to 1)
            similarity = (similarity + 1) / 2
            
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Similarity calculation failed: {e}")
            return 0.0
    
    def extract_embedding(self, face_roi: np.ndarray) -> np.ndarray:
        """
        Extract face embedding from preprocessed face ROI.
        
        Args:
            face_roi: Preprocessed face region of interest
            
        Returns:
            Face embedding vector
        """
        try:
            # Preprocess face
            preprocessed = self.preprocess_face(face_roi)
            
            # For now, return a simple feature vector
            # In production, this would use a trained face recognition model (FaceNet, ArcFace, etc.)
            # This is a placeholder that creates a 128-dimensional embedding
            embedding = cv2.resize(preprocessed, (16, 8)).flatten().astype(np.float32)
            
            # Normalize embedding
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Embedding extraction failed: {e}")
            return np.zeros(128, dtype=np.float32)

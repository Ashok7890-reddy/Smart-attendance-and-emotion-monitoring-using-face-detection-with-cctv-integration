#!/usr/bin/env python3
"""
Demonstration script for liveness detection functionality.

This script shows how to use the liveness detection service for anti-spoofing
in the Smart Attendance System.
"""

import cv2
import numpy as np
from datetime import datetime

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.liveness_detection_service import LivenessDetectionService
from backend.services.face_recognition_service import FaceRecognitionService
from backend.models.face_detection import CameraLocation


def create_test_frame(width=640, height=480):
    """Create a test video frame with some structure."""
    # Create a frame with some patterns to simulate a face-like structure
    frame = np.random.randint(50, 200, (height, width, 3), dtype=np.uint8)
    
    # Add some face-like features (simplified)
    center_x, center_y = width // 2, height // 2
    
    # Add a face-like oval
    cv2.ellipse(frame, (center_x, center_y), (80, 100), 0, 0, 360, (180, 150, 120), -1)
    
    # Add eyes
    cv2.circle(frame, (center_x - 25, center_y - 20), 8, (50, 50, 50), -1)
    cv2.circle(frame, (center_x + 25, center_y - 20), 8, (50, 50, 50), -1)
    
    # Add mouth
    cv2.ellipse(frame, (center_x, center_y + 30), (20, 10), 0, 0, 180, (100, 50, 50), -1)
    
    return frame


def demo_liveness_detection():
    """Demonstrate liveness detection functionality."""
    print("=== Smart Attendance System - Liveness Detection Demo ===\n")
    
    # Initialize services
    print("Initializing liveness detection service...")
    liveness_service = LivenessDetectionService()
    
    print("Initializing face recognition service...")
    face_service = FaceRecognitionService()
    
    print("\n1. Testing single frame liveness analysis:")
    print("-" * 50)
    
    # Test with a single frame
    test_frame = create_test_frame()
    result = liveness_service.analyze_frame(test_frame, "demo_session")
    
    print(f"Frame analysis result:")
    print(f"  - Is Live: {result.is_live}")
    print(f"  - Confidence: {result.confidence:.3f}")
    print(f"  - Blink Score: {result.blink_score:.3f}")
    print(f"  - Movement Score: {result.movement_score:.3f}")
    print(f"  - Texture Score: {result.texture_score:.3f}")
    print(f"  - Timestamp: {result.timestamp}")
    
    print("\n2. Testing sequence-based liveness verification:")
    print("-" * 50)
    
    # Create a sequence of frames with slight variations
    frame_sequence = []
    for i in range(35):  # Need at least 30 frames for verification
        frame = create_test_frame()
        # Add some variation to simulate movement
        noise = np.random.randint(-10, 10, frame.shape, dtype=np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        frame_sequence.append(frame)
    
    is_live = liveness_service.verify_liveness(frame_sequence, "demo_sequence")
    print(f"Sequence verification result: {'LIVE' if is_live else 'NOT LIVE'}")
    
    print("\n3. Testing face recognition with liveness scoring:")
    print("-" * 50)
    
    # Test face detection with liveness
    detections = face_service.detect_faces(test_frame, CameraLocation.CLASSROOM)
    print(f"Detected {len(detections)} faces")
    
    # Get liveness score
    liveness_score = face_service.get_liveness_score(test_frame, "demo_face")
    print(f"Liveness score from face recognition service: {liveness_score:.3f}")
    
    print("\n4. Testing session management:")
    print("-" * 50)
    
    # Get session statistics
    stats = liveness_service.get_session_stats("demo_session")
    print(f"Session statistics:")
    for key, value in stats.items():
        if key == 'start_time':
            print(f"  - {key}: {value}")
        else:
            print(f"  - {key}: {value}")
    
    print("\n5. Testing threshold updates:")
    print("-" * 50)
    
    # Update thresholds
    original_threshold = liveness_service.liveness_threshold
    print(f"Original liveness threshold: {original_threshold}")
    
    liveness_service.update_thresholds(liveness_threshold=0.8)
    print(f"Updated liveness threshold: {liveness_service.liveness_threshold}")
    
    # Test with new threshold
    result_new = liveness_service.analyze_frame(test_frame, "demo_threshold")
    print(f"Analysis with new threshold - Is Live: {result_new.is_live}")
    
    print("\n6. Testing anti-spoofing features:")
    print("-" * 50)
    
    # Create a "flat" image to simulate a photo attack
    flat_frame = np.full((480, 640, 3), 128, dtype=np.uint8)
    # Add a simple face pattern
    cv2.rectangle(flat_frame, (250, 150), (390, 330), (180, 150, 120), -1)
    cv2.circle(flat_frame, (290, 200), 5, (50, 50, 50), -1)
    cv2.circle(flat_frame, (350, 200), 5, (50, 50, 50), -1)
    
    flat_result = liveness_service.analyze_frame(flat_frame, "spoof_test")
    print(f"Flat image (potential spoof) analysis:")
    print(f"  - Is Live: {flat_result.is_live}")
    print(f"  - Confidence: {flat_result.confidence:.3f}")
    print(f"  - Texture Score: {flat_result.texture_score:.3f}")
    
    print("\n=== Demo Complete ===")
    print("\nKey Features Demonstrated:")
    print("✓ Eye blink detection for liveness verification")
    print("✓ Head movement analysis")
    print("✓ Texture analysis for photo/video spoof detection")
    print("✓ Real-time liveness scoring and validation")
    print("✓ Integration with face recognition service")
    print("✓ Session management and statistics")
    print("✓ Configurable thresholds")
    print("✓ Anti-spoofing capabilities")


if __name__ == "__main__":
    demo_liveness_detection()
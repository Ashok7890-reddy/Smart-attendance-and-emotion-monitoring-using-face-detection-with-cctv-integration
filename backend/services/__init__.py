# Services package
# Lazy imports to avoid loading heavy dependencies when not needed

__all__ = [
    'FaceRecognitionService',
    'LivenessDetectionService', 
    'EmotionAnalysisService'
]

def __getattr__(name):
    """Lazy import services to avoid loading heavy dependencies."""
    if name == 'FaceRecognitionService':
        from .face_recognition_service import FaceRecognitionService
        return FaceRecognitionService
    elif name == 'LivenessDetectionService':
        from .liveness_detection_service import LivenessDetectionService
        return LivenessDetectionService
    elif name == 'EmotionAnalysisService':
        from .emotion_analysis_service import EmotionAnalysisService
        return EmotionAnalysisService
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
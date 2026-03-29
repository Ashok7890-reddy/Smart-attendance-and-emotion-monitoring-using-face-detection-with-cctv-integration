"""
Fallback Emotion Analysis API endpoints.

This provides emotion analysis when DeepFace is not available,
using a lightweight OpenCV-based approach.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from backend.services.lightweight_emotion_service import lightweight_emotion_service
from backend.api.schemas import EmotionAnalysisRequest, EmotionAnalysisResponse


router = APIRouter(prefix="/api/v1/emotion-fallback", tags=["emotion-fallback"])


@router.post("/analyze-emotion-base64", response_model=Dict[str, Any])
async def analyze_emotion_fallback_endpoint(request: EmotionAnalysisRequest):
    """
    Analyze emotion using lightweight fallback method.
    
    Args:
        request: Emotion analysis request with base64 image
    
    Returns:
        Emotion analysis result
    """
    try:
        result = lightweight_emotion_service.analyze_emotion_from_base64(
            request.image_base64, 
            request.student_id
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallback emotion analysis failed: {str(e)}")


@router.get("/health")
async def health_check_fallback_endpoint():
    """
    Health check for fallback emotion analysis service.
    
    Returns:
        Service health status
    """
    try:
        health = lightweight_emotion_service.health_check()
        
        return {
            "success": True,
            "service": "lightweight_emotion_analysis",
            "status": "healthy" if health.get("status") == "healthy" else "unhealthy",
            "details": health
        }
        
    except Exception as e:
        return {
            "success": False,
            "service": "lightweight_emotion_analysis", 
            "status": "unhealthy",
            "error": str(e)
        }
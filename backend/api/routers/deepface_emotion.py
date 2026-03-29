"""
DeepFace Emotion Analysis API endpoints.
"""

import base64
import io
import numpy as np
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from PIL import Image
import cv2

from backend.services.deepface_emotion_service import deepface_emotion_service
from backend.api.schemas import EmotionAnalysisRequest, EmotionAnalysisResponse, BatchEmotionRequest
from backend.models.emotion import EmotionResult


router = APIRouter(prefix="/api/v1/deepface", tags=["deepface-emotion"])


@router.post("/analyze-emotion", response_model=EmotionAnalysisResponse)
async def analyze_emotion_endpoint(
    image: UploadFile = File(...),
    student_id: str = Form("unknown")
):
    """
    Analyze emotion from uploaded image using DeepFace.
    
    Args:
        image: Uploaded image file
        student_id: Student identifier
    
    Returns:
        Emotion analysis result with engagement score
    """
    try:
        # Read and validate image
        image_data = await image.read()
        
        if len(image_data) == 0:
            raise HTTPException(status_code=400, detail="Empty image file")
        
        # Convert to numpy array
        pil_image = Image.open(io.BytesIO(image_data))
        image_np = np.array(pil_image)
        
        # Convert RGB to BGR for OpenCV
        if len(image_np.shape) == 3 and image_np.shape[2] == 3:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        
        # Analyze emotion
        result = deepface_emotion_service.analyze_emotion(image_np, student_id)
        
        return EmotionAnalysisResponse(
            success=True,
            student_id=result.student_id,
            emotion=result.emotion.value,
            raw_emotion=result.raw_emotion,
            confidence=result.confidence,
            engagement_score=result.engagement_score,
            timestamp=result.timestamp.isoformat(),
            emotion_breakdown=result.emotion_breakdown
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emotion analysis failed: {str(e)}")


@router.post("/analyze-emotion-base64", response_model=EmotionAnalysisResponse)
async def analyze_emotion_base64_endpoint(request: EmotionAnalysisRequest):
    """
    Analyze emotion from base64 encoded image using DeepFace.
    
    Args:
        request: Emotion analysis request with base64 image
    
    Returns:
        Emotion analysis result with engagement score
    """
    try:
        # Analyze emotion from base64
        result = deepface_emotion_service.analyze_emotion_from_base64(
            request.image_base64, 
            request.student_id
        )
        
        return EmotionAnalysisResponse(
            success=True,
            student_id=result.student_id,
            emotion=result.emotion.value,
            raw_emotion=result.raw_emotion,
            confidence=result.confidence,
            engagement_score=result.engagement_score,
            timestamp=result.timestamp.isoformat(),
            emotion_breakdown=result.emotion_breakdown
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emotion analysis failed: {str(e)}")


@router.post("/analyze-batch-emotions")
async def analyze_batch_emotions_endpoint(request: BatchEmotionRequest):
    """
    Analyze emotions for multiple images in batch using DeepFace.
    
    Args:
        request: Batch emotion analysis request
    
    Returns:
        List of emotion analysis results
    """
    try:
        images = []
        
        # Decode all base64 images
        for i, image_b64 in enumerate(request.images_base64):
            try:
                image_data = base64.b64decode(image_b64)
                pil_image = Image.open(io.BytesIO(image_data))
                image_np = np.array(pil_image)
                
                # Convert RGB to BGR for OpenCV
                if len(image_np.shape) == 3 and image_np.shape[2] == 3:
                    image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
                
                images.append(image_np)
                
            except Exception as e:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Failed to decode image {i}: {str(e)}"
                )
        
        # Analyze emotions asynchronously
        results = await deepface_emotion_service.analyze_batch_emotions_async(
            images, 
            request.student_ids
        )
        
        # Convert results to response format
        response_results = []
        for result in results:
            response_results.append({
                "success": True,
                "student_id": result.student_id,
                "emotion": result.emotion.value,
                "raw_emotion": result.raw_emotion,
                "confidence": result.confidence,
                "engagement_score": result.engagement_score,
                "timestamp": result.timestamp.isoformat(),
                "emotion_breakdown": result.emotion_breakdown
            })
        
        return {
            "success": True,
            "total_processed": len(response_results),
            "results": response_results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch emotion analysis failed: {str(e)}")


@router.get("/session-statistics/{session_id}")
async def get_session_statistics_endpoint(session_id: str):
    """
    Get comprehensive emotion statistics for a session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Detailed emotion statistics and analytics
    """
    try:
        stats = deepface_emotion_service.get_emotion_statistics_summary(session_id)
        
        if "error" in stats:
            raise HTTPException(status_code=404, detail=stats["error"])
        
        return {
            "success": True,
            "session_id": session_id,
            "statistics": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session statistics: {str(e)}")


@router.get("/real-time-metrics/{session_id}")
async def get_real_time_metrics_endpoint(session_id: str):
    """
    Get real-time engagement metrics for a session.
    
    Args:
        session_id: Session identifier
    
    Returns:
        Real-time engagement metrics
    """
    try:
        metrics = deepface_emotion_service.get_real_time_metrics(session_id)
        
        if metrics is None:
            raise HTTPException(status_code=404, detail="Session not found or no metrics available")
        
        return {
            "success": True,
            "session_id": session_id,
            "metrics": metrics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get real-time metrics: {str(e)}")


@router.get("/active-sessions")
async def get_active_sessions_endpoint():
    """
    Get list of all active emotion analysis sessions.
    
    Returns:
        List of active session IDs
    """
    try:
        sessions = deepface_emotion_service.get_active_sessions()
        
        return {
            "success": True,
            "active_sessions": sessions,
            "total_sessions": len(sessions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active sessions: {str(e)}")


@router.post("/update-session/{session_id}")
async def update_session_endpoint(
    session_id: str,
    image: UploadFile = File(...),
    student_id: str = Form("unknown")
):
    """
    Update session with new emotion analysis result.
    
    Args:
        session_id: Session identifier
        image: Uploaded image file
        student_id: Student identifier
    
    Returns:
        Updated session statistics
    """
    try:
        # Read and process image
        image_data = await image.read()
        pil_image = Image.open(io.BytesIO(image_data))
        image_np = np.array(pil_image)
        
        # Convert RGB to BGR for OpenCV
        if len(image_np.shape) == 3 and image_np.shape[2] == 3:
            image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        
        # Analyze emotion
        result = deepface_emotion_service.analyze_emotion(image_np, student_id)
        
        # Update session statistics
        deepface_emotion_service.update_session_statistics(session_id, result)
        
        # Get updated statistics
        stats = deepface_emotion_service.get_session_statistics(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "emotion_result": {
                "student_id": result.student_id,
                "emotion": result.emotion.value,
                "raw_emotion": result.raw_emotion,
                "confidence": result.confidence,
                "engagement_score": result.engagement_score,
                "timestamp": result.timestamp.isoformat()
            },
            "session_statistics": {
                "total_frames": stats.total_frames,
                "average_engagement": stats.average_engagement_score,
                "emotion_distribution": {k.value: v for k, v in stats.emotion_percentages.items()}
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update session: {str(e)}")


@router.get("/health")
async def health_check_endpoint():
    """
    Health check for DeepFace emotion analysis service.
    
    Returns:
        Service health status and configuration
    """
    try:
        health = deepface_emotion_service.health_check()
        
        return {
            "success": True,
            "service": "deepface_emotion_analysis",
            "status": "healthy" if health.get("status") == "healthy" else "unhealthy",
            "details": health
        }
        
    except Exception as e:
        return {
            "success": False,
            "service": "deepface_emotion_analysis",
            "status": "unhealthy",
            "error": str(e)
        }


@router.delete("/cleanup-sessions")
async def cleanup_old_sessions_endpoint(max_age_hours: int = 24):
    """
    Clean up old inactive sessions.
    
    Args:
        max_age_hours: Maximum age in hours for sessions to keep
    
    Returns:
        Cleanup result
    """
    try:
        deepface_emotion_service.cleanup_old_sessions(max_age_hours)
        
        return {
            "success": True,
            "message": f"Cleaned up sessions older than {max_age_hours} hours"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup sessions: {str(e)}")
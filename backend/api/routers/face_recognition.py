"""
Face recognition API endpoints.
"""

import base64
import io
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from PIL import Image
import numpy as np

from ..schemas import FaceRecognitionRequest, FaceRecognitionResponse, MultipleFaceRecognitionResponse
from ..dependencies import (
    get_student_repository, get_face_recognition_service,
    require_faculty_role
)
from ...database.repositories import StudentRepository
from ...services.face_recognition_service import FaceRecognitionService
from ...core.encryption import decrypt_data

router = APIRouter()


@router.post("/recognize", response_model=FaceRecognitionResponse)
async def recognize_face(
    face_data: FaceRecognitionRequest,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    face_recognition_service: Annotated[FaceRecognitionService, Depends(get_face_recognition_service)]
):
    """
    Recognize a single face in an image and return student information.
    
    Requirements: 1.1, 1.2, 1.5
    - Capture and process facial features for recognition
    - Complete facial recognition processing within 2 seconds
    """
    try:
        # Decode base64 image
        try:
            image_data = base64.b64decode(face_data.image_data)
            image = Image.open(io.BytesIO(image_data))
            image_array = np.array(image)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image data: {str(e)}"
            )
        
        # Detect faces in the image
        detections = face_recognition_service.detect_faces(image_array)
        if not detections:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No face detected in the provided image"
            )
        
        if len(detections) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple faces detected. Please provide an image with a single face"
            )
        
        detection = detections[0]
        
        # Verify liveness
        if detection.liveness_score < 0.7:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Face liveness check failed. Please provide a live photo"
            )
        
        # Extract face embedding
        face_roi = image_array[
            detection.bounding_box[1]:detection.bounding_box[3],
            detection.bounding_box[0]:detection.bounding_box[2]
        ]
        embedding = face_recognition_service.extract_embedding(face_roi)
        
        # Get all active students with face embeddings
        all_students = await student_repo.get_students_with_filters(
            filters={'is_active': True},
            skip=0,
            limit=10000
        )
        
        # Filter students with face embeddings
        students_with_faces = [s for s in all_students if s.face_embedding and len(s.face_embedding) > 0]
        
        if not students_with_faces:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No registered students found in the database"
            )
        
        # Match face against all registered students
        best_match = None
        best_similarity = 0.0
        
        for student in students_with_faces:
            try:
                # Decrypt and load student's face embedding
                decrypted_embedding = decrypt_data(student.face_embedding)
                student_embedding = np.frombuffer(decrypted_embedding, dtype=np.float32)
                
                # Calculate similarity
                similarity = face_recognition_service.calculate_similarity(embedding, student_embedding)
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = student
            except Exception as e:
                print(f"Error processing student {student.student_id}: {str(e)}")
                continue
        
        # Check if match confidence is above threshold
        if best_similarity < 0.75:  # 75% confidence threshold
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching student found. Face not recognized"
            )
        
        return FaceRecognitionResponse(
            student_id=best_match.student_id,
            name=best_match.name,
            student_type=best_match.student_type.value,
            confidence=float(best_similarity),
            bounding_box=detection.bounding_box,
            liveness_score=detection.liveness_score
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recognize face: {str(e)}"
        )


@router.post("/recognize-multiple", response_model=MultipleFaceRecognitionResponse)
async def recognize_multiple_faces(
    face_data: FaceRecognitionRequest,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    face_recognition_service: Annotated[FaceRecognitionService, Depends(get_face_recognition_service)]
):
    """
    Recognize multiple faces in an image (for classroom attendance).
    
    Requirements: 1.2, 1.3
    - Detect and identify multiple faces in classroom
    - Maintain real-time database of detected student faces
    """
    try:
        # Decode base64 image
        try:
            image_data = base64.b64decode(face_data.image_data)
            image = Image.open(io.BytesIO(image_data))
            image_array = np.array(image)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image data: {str(e)}"
            )
        
        # Detect all faces in the image
        detections = face_recognition_service.detect_faces(image_array)
        if not detections:
            return MultipleFaceRecognitionResponse(
                detections=[],
                total_faces=0
            )
        
        # Get all active students with face embeddings
        all_students = await student_repo.get_students_with_filters(
            filters={'is_active': True},
            skip=0,
            limit=10000
        )
        
        # Filter students with face embeddings
        students_with_faces = [s for s in all_students if s.face_embedding and len(s.face_embedding) > 0]
        
        if not students_with_faces:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No registered students found in the database"
            )
        
        # Process each detected face
        recognized_students = []
        
        for detection in detections:
            # Skip faces with low liveness score
            if detection.liveness_score < 0.6:
                continue
            
            # Extract face embedding
            face_roi = image_array[
                detection.bounding_box[1]:detection.bounding_box[3],
                detection.bounding_box[0]:detection.bounding_box[2]
            ]
            embedding = face_recognition_service.extract_embedding(face_roi)
            
            # Match face against all registered students
            best_match = None
            best_similarity = 0.0
            
            for student in students_with_faces:
                try:
                    # Decrypt and load student's face embedding
                    decrypted_embedding = decrypt_data(student.face_embedding)
                    student_embedding = np.frombuffer(decrypted_embedding, dtype=np.float32)
                    
                    # Calculate similarity
                    similarity = face_recognition_service.calculate_similarity(embedding, student_embedding)
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = student
                except Exception as e:
                    print(f"Error processing student {student.student_id}: {str(e)}")
                    continue
            
            # Add to results if confidence is above threshold
            if best_match and best_similarity >= 0.70:  # 70% confidence threshold for classroom
                recognized_students.append(FaceRecognitionResponse(
                    student_id=best_match.student_id,
                    name=best_match.name,
                    student_type=best_match.student_type.value,
                    confidence=float(best_similarity),
                    bounding_box=detection.bounding_box,
                    liveness_score=detection.liveness_score
                ))
        
        return MultipleFaceRecognitionResponse(
            detections=recognized_students,
            total_faces=len(detections)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recognize faces: {str(e)}"
        )

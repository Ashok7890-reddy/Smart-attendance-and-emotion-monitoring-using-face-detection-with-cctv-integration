"""
Student management API endpoints.
"""

import base64
import io
from datetime import datetime
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from PIL import Image
import numpy as np

from ..schemas import (
    StudentCreate, StudentUpdate, StudentResponse, 
    FaceRegistrationRequest, BulkStudentCreate, BulkOperationResponse
)
from ..dependencies import (
    get_student_repository, get_face_recognition_service,
    require_faculty_role, require_admin_role
)
from ...database.repositories import StudentRepository
from ...services.face_recognition_service import FaceRecognitionService
from ...models.student import Student, StudentType
from ...core.encryption import encrypt_data

router = APIRouter()


@router.post("/", response_model=StudentResponse)
async def create_student(
    student_data: StudentCreate,
    current_user: Annotated[dict, Depends(require_admin_role)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)]
):
    """
    Create a new student.
    
    Requirements: 5.1, 5.2
    - Create endpoints for student enrollment and face registration
    """
    try:
        # Check if student already exists
        existing_student = await student_repo.get_student_by_id(student_data.student_id)
        if existing_student:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Student with ID {student_data.student_id} already exists"
            )
        
        # Create student object
        student = Student(
            student_id=student_data.student_id,
            name=student_data.name,
            student_type=StudentType(student_data.student_type.value),
            face_embedding=b"",  # Will be set during face registration
            enrollment_date=datetime.utcnow(),
            is_active=True,
            email=student_data.email,
            phone=student_data.phone,
            class_id=student_data.class_id
        )
        
        # Save student to database
        created_student = await student_repo.create_student(student)
        
        return StudentResponse(
            student_id=created_student.student_id,
            name=created_student.name,
            student_type=created_student.student_type.value,
            enrollment_date=created_student.enrollment_date,
            is_active=created_student.is_active,
            email=created_student.email,
            phone=created_student.phone,
            class_id=created_student.class_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create student: {str(e)}"
        )


@router.get("/", response_model=List[StudentResponse])
async def get_students(
    current_user: Annotated[dict, Depends(require_faculty_role)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    class_id: Optional[str] = Query(None, description="Filter by class ID"),
    student_type: Optional[str] = Query(None, description="Filter by student type"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return")
):
    """
    Get list of students with optional filtering.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Apply filters
        filters = {}
        if class_id:
            filters['class_id'] = class_id
        if student_type:
            filters['student_type'] = StudentType(student_type)
        if is_active is not None:
            filters['is_active'] = is_active
        
        # Get students from database
        students = await student_repo.get_students_with_filters(
            filters=filters,
            skip=skip,
            limit=limit
        )
        
        return [
            StudentResponse(
                student_id=student.student_id,
                name=student.name,
                student_type=student.student_type.value,
                enrollment_date=student.enrollment_date,
                is_active=student.is_active,
                email=student.email,
                phone=student.phone,
                class_id=student.class_id
            )
            for student in students
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve students: {str(e)}"
        )


@router.get("/{student_id}", response_model=StudentResponse)
async def get_student(
    student_id: str,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)]
):
    """
    Get student by ID.
    
    Requirements: 5.1, 5.2
    """
    try:
        student = await student_repo.get_student_by_id(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with ID {student_id} not found"
            )
        
        return StudentResponse(
            student_id=student.student_id,
            name=student.name,
            student_type=student.student_type.value,
            enrollment_date=student.enrollment_date,
            is_active=student.is_active,
            email=student.email,
            phone=student.phone,
            class_id=student.class_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve student: {str(e)}"
        )


@router.put("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: str,
    student_data: StudentUpdate,
    current_user: Annotated[dict, Depends(require_admin_role)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)]
):
    """
    Update student information.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Check if student exists
        existing_student = await student_repo.get_student_by_id(student_id)
        if not existing_student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with ID {student_id} not found"
            )
        
        # Prepare update data
        update_data = {}
        if student_data.name is not None:
            update_data['name'] = student_data.name
        if student_data.student_type is not None:
            update_data['student_type'] = StudentType(student_data.student_type.value)
        if student_data.email is not None:
            update_data['email'] = student_data.email
        if student_data.phone is not None:
            update_data['phone'] = student_data.phone
        if student_data.class_id is not None:
            update_data['class_id'] = student_data.class_id
        if student_data.is_active is not None:
            update_data['is_active'] = student_data.is_active
        
        # Update student
        updated_student = await student_repo.update_student(student_id, update_data)
        
        return StudentResponse(
            student_id=updated_student.student_id,
            name=updated_student.name,
            student_type=updated_student.student_type.value,
            enrollment_date=updated_student.enrollment_date,
            is_active=updated_student.is_active,
            email=updated_student.email,
            phone=updated_student.phone,
            class_id=updated_student.class_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update student: {str(e)}"
        )


@router.delete("/{student_id}")
async def delete_student(
    student_id: str,
    current_user: Annotated[dict, Depends(require_admin_role)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)]
):
    """
    Delete student (soft delete by setting is_active=False).
    
    Requirements: 5.1, 5.2
    """
    try:
        # Check if student exists
        existing_student = await student_repo.get_student_by_id(student_id)
        if not existing_student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with ID {student_id} not found"
            )
        
        # Soft delete by setting is_active=False
        await student_repo.update_student(student_id, {'is_active': False})
        
        return {"message": f"Student {student_id} has been deactivated"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete student: {str(e)}"
        )


@router.post("/{student_id}/register-face")
async def register_face(
    student_id: str,
    face_data: FaceRegistrationRequest,
    current_user: Annotated[dict, Depends(require_admin_role)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)],
    face_recognition_service: Annotated[FaceRecognitionService, Depends(get_face_recognition_service)]
):
    """
    Register face embedding for a student.
    
    Requirements: 5.1, 5.2
    - Create endpoints for student enrollment and face registration
    """
    try:
        # Check if student exists
        student = await student_repo.get_student_by_id(student_id)
        if not student:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student with ID {student_id} not found"
            )
        
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No face detected in the provided image"
            )
        
        if len(detections) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Multiple faces detected. Please provide an image with a single face"
            )
        
        # Extract face embedding
        detection = detections[0]
        
        # Verify liveness (basic check for registration)
        if detection.liveness_score < 0.5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Face liveness check failed. Please provide a live photo"
            )
        
        # Extract and encrypt face embedding
        embedding = face_recognition_service.extract_embedding(
            image_array[
                detection.bounding_box[1]:detection.bounding_box[3],
                detection.bounding_box[0]:detection.bounding_box[2]
            ]
        )
        
        encrypted_embedding = encrypt_data(embedding.tobytes())
        
        # Update student with face embedding
        await student_repo.update_student(student_id, {
            'face_embedding': encrypted_embedding
        })
        
        return {
            "message": f"Face registered successfully for student {student_id}",
            "embedding_size": len(embedding),
            "liveness_score": detection.liveness_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register face: {str(e)}"
        )


@router.post("/bulk", response_model=BulkOperationResponse)
async def create_students_bulk(
    bulk_data: BulkStudentCreate,
    current_user: Annotated[dict, Depends(require_admin_role)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)]
):
    """
    Create multiple students in bulk.
    
    Requirements: 5.1, 5.2
    """
    try:
        results = []
        errors = []
        successful_count = 0
        
        for i, student_data in enumerate(bulk_data.students):
            try:
                # Check if student already exists
                existing_student = await student_repo.get_student_by_id(student_data.student_id)
                if existing_student:
                    errors.append({
                        "index": i,
                        "student_id": student_data.student_id,
                        "error": "Student already exists"
                    })
                    continue
                
                # Create student
                student = Student(
                    student_id=student_data.student_id,
                    name=student_data.name,
                    student_type=StudentType(student_data.student_type.value),
                    face_embedding=b"",
                    enrollment_date=datetime.utcnow(),
                    is_active=True,
                    email=student_data.email,
                    phone=student_data.phone,
                    class_id=student_data.class_id
                )
                
                created_student = await student_repo.create_student(student)
                successful_count += 1
                
                results.append({
                    "index": i,
                    "student_id": created_student.student_id,
                    "status": "created"
                })
                
            except Exception as e:
                errors.append({
                    "index": i,
                    "student_id": student_data.student_id,
                    "error": str(e)
                })
        
        return BulkOperationResponse(
            total_items=len(bulk_data.students),
            successful_items=successful_count,
            failed_items=len(errors),
            errors=errors,
            results=results
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process bulk student creation: {str(e)}"
        )


@router.get("/class/{class_id}", response_model=List[StudentResponse])
async def get_students_by_class(
    class_id: str,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    student_repo: Annotated[StudentRepository, Depends(get_student_repository)]
):
    """
    Get all students in a specific class.
    
    Requirements: 5.1, 5.2
    """
    try:
        students = await student_repo.get_students_by_class(class_id)
        
        return [
            StudentResponse(
                student_id=student.student_id,
                name=student.name,
                student_type=student.student_type.value,
                enrollment_date=student.enrollment_date,
                is_active=student.is_active,
                email=student.email,
                phone=student.phone,
                class_id=student.class_id
            )
            for student in students
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve students for class {class_id}: {str(e)}"
        )
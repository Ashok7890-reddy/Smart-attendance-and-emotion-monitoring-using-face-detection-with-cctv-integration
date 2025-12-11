"""
Session management API endpoints.
"""

from datetime import datetime
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from ..schemas import (
    SessionCreate, SessionResponse, SessionUpdate,
    RealTimeAttendanceResponse
)
from ..dependencies import (
    get_attendance_service, require_faculty_role, require_admin_role
)
from ...services.attendance_service import AttendanceService, ClassroomAttendanceProcessor
from ...models.attendance import AttendanceSession

router = APIRouter()


@router.post("/", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Create a new attendance session.
    
    Requirements: 5.1, 5.2
    - Implement API endpoints for attendance session management
    """
    try:
        # Create classroom attendance processor
        classroom_processor = ClassroomAttendanceProcessor(attendance_service)
        
        # Start new session
        session_id = await classroom_processor.start_classroom_session(
            class_id=session_data.class_id,
            faculty_id=session_data.faculty_id
        )
        
        # Get the created session
        session = await attendance_service.attendance_repo.get_session_by_id(session_id)
        
        return SessionResponse(
            session_id=session.session_id,
            class_id=session.class_id,
            faculty_id=session.faculty_id,
            start_time=session.start_time,
            end_time=session.end_time,
            total_registered=session.total_registered,
            total_detected=session.total_detected,
            is_active=session.is_active
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.get("/", response_model=List[SessionResponse])
async def get_sessions(
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)],
    class_id: Optional[str] = Query(None, description="Filter by class ID"),
    faculty_id: Optional[str] = Query(None, description="Filter by faculty ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    start_date: Optional[datetime] = Query(None, description="Filter sessions from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter sessions until this date"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return")
):
    """
    Get list of attendance sessions with optional filtering.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Build filters
        filters = {}
        if class_id:
            filters['class_id'] = class_id
        if faculty_id:
            filters['faculty_id'] = faculty_id
        if is_active is not None:
            filters['is_active'] = is_active
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        
        # Get sessions from database
        sessions = await attendance_service.attendance_repo.get_sessions_with_filters(
            filters=filters,
            skip=skip,
            limit=limit
        )
        
        return [
            SessionResponse(
                session_id=session.session_id,
                class_id=session.class_id,
                faculty_id=session.faculty_id,
                start_time=session.start_time,
                end_time=session.end_time,
                total_registered=session.total_registered,
                total_detected=session.total_detected,
                is_active=session.is_active
            )
            for session in sessions
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sessions: {str(e)}"
        )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Get session by ID.
    
    Requirements: 5.1, 5.2
    """
    try:
        session = await attendance_service.attendance_repo.get_session_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found"
            )
        
        return SessionResponse(
            session_id=session.session_id,
            class_id=session.class_id,
            faculty_id=session.faculty_id,
            start_time=session.start_time,
            end_time=session.end_time,
            total_registered=session.total_registered,
            total_detected=session.total_detected,
            is_active=session.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session: {str(e)}"
        )


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    session_data: SessionUpdate,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Update session information.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Check if session exists
        existing_session = await attendance_service.attendance_repo.get_session_by_id(session_id)
        if not existing_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found"
            )
        
        # Prepare update data
        update_data = {}
        if session_data.end_time is not None:
            update_data['end_time'] = session_data.end_time
        if session_data.is_active is not None:
            update_data['is_active'] = session_data.is_active
        
        # Update session
        updated_session = await attendance_service.attendance_repo.update_session(
            session_id, update_data
        )
        
        return SessionResponse(
            session_id=updated_session.session_id,
            class_id=updated_session.class_id,
            faculty_id=updated_session.faculty_id,
            start_time=updated_session.start_time,
            end_time=updated_session.end_time,
            total_registered=updated_session.total_registered,
            total_detected=updated_session.total_detected,
            is_active=updated_session.is_active
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update session: {str(e)}"
        )


@router.post("/{session_id}/end")
async def end_session(
    session_id: str,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    End an active attendance session.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Create classroom attendance processor
        classroom_processor = ClassroomAttendanceProcessor(attendance_service)
        
        # End the session
        success = await classroom_processor.end_classroom_session(session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found or already ended"
            )
        
        return {"message": f"Session {session_id} has been ended successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}"
        )


@router.get("/{session_id}/real-time", response_model=RealTimeAttendanceResponse)
async def get_real_time_attendance(
    session_id: str,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Get real-time attendance data for a session.
    
    Requirements: 5.2, 5.3
    - Display current attendance percentage for the active session
    - Present emotion statistics as interactive graphs
    """
    try:
        # Create classroom attendance processor
        classroom_processor = ClassroomAttendanceProcessor(attendance_service)
        
        # Get real-time attendance data
        attendance_data = await classroom_processor.get_real_time_attendance(session_id)
        
        if not attendance_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found"
            )
        
        return RealTimeAttendanceResponse(
            session_id=attendance_data['session_id'],
            class_id=attendance_data['class_id'],
            total_registered=attendance_data['total_registered'],
            total_present=attendance_data['total_present'],
            total_absent=attendance_data['total_absent'],
            attendance_percentage=attendance_data['attendance_percentage'],
            present_students=attendance_data['present_students'],
            absent_students=attendance_data['absent_students'],
            session_start=datetime.fromisoformat(attendance_data['session_start']),
            is_active=attendance_data['is_active']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get real-time attendance: {str(e)}"
        )


@router.get("/{session_id}/statistics")
async def get_session_statistics(
    session_id: str,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Get comprehensive statistics for a session.
    
    Requirements: 5.2, 5.3
    """
    try:
        # Get session
        session = await attendance_service.attendance_repo.get_session_by_id(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with ID {session_id} not found"
            )
        
        # Get attendance records
        attendance_records = await attendance_service.attendance_repo.get_session_attendance(session_id)
        
        # Calculate statistics
        total_registered = session.total_registered
        total_present = len([r for r in attendance_records if r.status.value == "present"])
        total_absent = total_registered - total_present
        attendance_rate = (total_present / total_registered * 100) if total_registered > 0 else 0
        
        # Get day scholar and hostel student breakdown
        day_scholar_count = len([r for r in attendance_records 
                               if r.student_id and await _is_day_scholar(r.student_id, attendance_service)])
        hostel_student_count = total_present - day_scholar_count
        
        return {
            "session_id": session_id,
            "session_info": {
                "class_id": session.class_id,
                "faculty_id": session.faculty_id,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "duration_minutes": (
                    (session.end_time - session.start_time).total_seconds() / 60
                    if session.end_time else None
                )
            },
            "attendance_statistics": {
                "total_registered": total_registered,
                "total_present": total_present,
                "total_absent": total_absent,
                "attendance_rate": round(attendance_rate, 2),
                "day_scholar_present": day_scholar_count,
                "hostel_student_present": hostel_student_count
            },
            "timing_statistics": {
                "session_start": session.start_time.isoformat(),
                "first_detection": min([r.timestamp for r in attendance_records]).isoformat() if attendance_records else None,
                "last_detection": max([r.timestamp for r in attendance_records]).isoformat() if attendance_records else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session statistics: {str(e)}"
        )


async def _is_day_scholar(student_id: str, attendance_service: AttendanceService) -> bool:
    """Helper function to check if student is a day scholar."""
    try:
        student = await attendance_service.student_repo.get_student_by_id(student_id)
        return student and student.student_type.value == "day_scholar"
    except:
        return False
"""
Attendance management API endpoints.
"""

from datetime import datetime
from typing import Annotated, List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query

from ..schemas import (
    GateEntryRequest, ClassroomAttendanceRequest, AttendanceReportRequest,
    AttendanceReportResponse, AttendanceRecordResponse, ValidationRequest,
    ValidationResponse, CrossVerificationResponse
)
from ..dependencies import (
    get_attendance_service, get_validation_service,
    require_faculty_role, require_admin_role
)
from ...services.attendance_service import (
    AttendanceService, GateEntryTracker, 
    CrossVerificationProcessor, HostelStudentProcessor
)
from ...services.validation_service import ValidationService
from ...models.face_detection import FaceDetection, CameraLocation

router = APIRouter()


@router.post("/gate-entry")
async def record_gate_entry(
    gate_entry: GateEntryRequest,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Record gate entry for a day scholar.
    
    Requirements: 5.1, 5.2
    - Implement API endpoints for attendance session management
    """
    try:
        success = await attendance_service.record_gate_entry(
            student_id=gate_entry.student_id,
            timestamp=gate_entry.timestamp
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to record gate entry for student {gate_entry.student_id}"
            )
        
        return {
            "message": f"Gate entry recorded successfully for student {gate_entry.student_id}",
            "student_id": gate_entry.student_id,
            "timestamp": gate_entry.timestamp.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record gate entry: {str(e)}"
        )


@router.post("/classroom")
async def mark_classroom_attendance(
    classroom_data: ClassroomAttendanceRequest,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Mark classroom attendance based on face detections.
    
    Requirements: 5.1, 5.2
    - Implement API endpoints for attendance session management
    """
    try:
        # Convert detection data to FaceDetection objects
        detections = []
        for detection_data in classroom_data.detections:
            detection = FaceDetection(
                bounding_box=tuple(detection_data.get('bounding_box', [0, 0, 100, 100])),
                confidence=detection_data.get('confidence', 0.0),
                embedding=detection_data.get('embedding', []),
                liveness_score=detection_data.get('liveness_score', 0.0),
                timestamp=datetime.utcnow(),
                camera_location=CameraLocation.CLASSROOM
            )
            detections.append(detection)
        
        # Mark attendance
        session = await attendance_service.mark_classroom_attendance(detections)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to mark classroom attendance"
            )
        
        return {
            "message": "Classroom attendance marked successfully",
            "session_id": session.session_id,
            "total_detected": session.total_detected,
            "total_registered": session.total_registered,
            "attendance_percentage": (
                (session.total_detected / session.total_registered * 100) 
                if session.total_registered > 0 else 0
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark classroom attendance: {str(e)}"
        )


@router.get("/session/{session_id}/records", response_model=List[AttendanceRecordResponse])
async def get_attendance_records(
    session_id: str,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Get attendance records for a session.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Get attendance records
        records = await attendance_service.attendance_repo.get_session_attendance(session_id)
        
        return [
            AttendanceRecordResponse(
                student_id=record.student_id,
                session_id=record.session_id,
                status=record.status.value,
                timestamp=record.timestamp,
                confidence=record.confidence,
                gate_entry_time=record.gate_entry_time,
                classroom_entry_time=record.classroom_entry_time
            )
            for record in records
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get attendance records: {str(e)}"
        )


@router.post("/report", response_model=AttendanceReportResponse)
async def generate_attendance_report(
    report_request: AttendanceReportRequest,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Generate comprehensive attendance report.
    
    Requirements: 5.5
    - Generate downloadable attendance reports with date, time, and engagement metrics
    """
    try:
        # Generate report
        report_data = await attendance_service.generate_attendance_report(
            session_id=report_request.session_id
        )
        
        if 'error' in report_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=report_data['error']
            )
        
        return AttendanceReportResponse(
            session_info=report_data['session_info'],
            overall_statistics=report_data['overall_statistics'],
            day_scholar_report=report_data['day_scholar_report'],
            hostel_student_report=report_data['hostel_student_report'],
            alerts=report_data['alerts'],
            generated_at=datetime.fromisoformat(report_data['generated_at'])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate attendance report: {str(e)}"
        )


@router.post("/validate", response_model=ValidationResponse)
async def validate_attendance(
    validation_request: ValidationRequest,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    validation_service: Annotated[ValidationService, Depends(get_validation_service)]
):
    """
    Validate attendance accuracy for a session.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Get session
        session = await validation_service.attendance_service.attendance_repo.get_session_by_id(
            validation_request.session_id
        )
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {validation_request.session_id} not found"
            )
        
        # Validate attendance
        validation_result = await validation_service.validate_attendance_count(session)
        missing_students = await validation_service.check_missing_students(session)
        
        return ValidationResponse(
            session_id=validation_request.session_id,
            validation_status=validation_result.get('status', 'unknown'),
            total_registered=session.total_registered,
            total_detected=session.total_detected,
            missing_students=[
                {
                    'student_id': student.student_id,
                    'name': student.name,
                    'student_type': student.student_type.value
                }
                for student in missing_students
            ],
            alerts=validation_result.get('alerts', []),
            validation_timestamp=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate attendance: {str(e)}"
        )


@router.get("/cross-verification/{session_id}", response_model=CrossVerificationResponse)
async def get_cross_verification_results(
    session_id: str,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Get cross-verification results for day scholars.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Create cross-verification processor
        cross_verifier = CrossVerificationProcessor(attendance_service)
        
        # Run cross-verification
        verification_results = await cross_verifier.run_cross_verification(session_id)
        
        if 'error' in verification_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=verification_results['error']
            )
        
        return CrossVerificationResponse(
            session_id=verification_results['session_id'],
            total_day_scholars=verification_results['total_day_scholars'],
            verified_count=verification_results['verified_count'],
            incomplete_count=verification_results['incomplete_count'],
            verification_rate=round(
                (verification_results['verified_count'] / verification_results['total_day_scholars'] * 100)
                if verification_results['total_day_scholars'] > 0 else 0, 2
            ),
            missing_gate_entry=verification_results.get('missing_gate_entry', []),
            timing_violations=verification_results.get('timing_violations', []),
            alerts=verification_results.get('alerts', [])
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cross-verification results: {str(e)}"
        )


@router.post("/fix-incomplete/{student_id}/{session_id}")
async def fix_incomplete_attendance(
    student_id: str,
    session_id: str,
    current_user: Annotated[dict, Depends(require_admin_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)],
    manual_gate_time: Optional[datetime] = Query(None, description="Manual gate entry time")
):
    """
    Manually fix incomplete attendance for a day scholar.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Create cross-verification processor
        cross_verifier = CrossVerificationProcessor(attendance_service)
        
        # Fix incomplete attendance
        success = await cross_verifier.fix_incomplete_attendance(
            student_id=student_id,
            session_id=session_id,
            manual_gate_time=manual_gate_time
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to fix incomplete attendance for student {student_id}"
            )
        
        return {
            "message": f"Incomplete attendance fixed for student {student_id}",
            "student_id": student_id,
            "session_id": session_id,
            "manual_gate_time": manual_gate_time.isoformat() if manual_gate_time else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fix incomplete attendance: {str(e)}"
        )


@router.get("/hostel-students/{session_id}")
async def get_hostel_student_attendance(
    session_id: str,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Get hostel student attendance for a session.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Create hostel student processor
        hostel_processor = HostelStudentProcessor(attendance_service)
        
        # Get hostel student attendance
        hostel_results = await hostel_processor.validate_hostel_attendance(session_id)
        
        if 'error' in hostel_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=hostel_results['error']
            )
        
        return hostel_results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hostel student attendance: {str(e)}"
        )


@router.get("/daily-summary")
async def get_daily_attendance_summary(
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)],
    date: datetime = Query(..., description="Date for summary (YYYY-MM-DD)")
):
    """
    Get daily attendance summary across all sessions.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Get all sessions for the date
        sessions = await attendance_service.attendance_repo.get_sessions_by_date(date)
        
        daily_summary = {
            "date": date.strftime("%Y-%m-%d"),
            "total_sessions": len(sessions),
            "total_students_registered": 0,
            "total_students_present": 0,
            "overall_attendance_rate": 0.0,
            "sessions": []
        }
        
        total_registered = 0
        total_present = 0
        
        for session in sessions:
            # Get attendance records for session
            records = await attendance_service.attendance_repo.get_session_attendance(session.session_id)
            present_count = len([r for r in records if r.status.value == "present"])
            
            session_data = {
                "session_id": session.session_id,
                "class_id": session.class_id,
                "faculty_id": session.faculty_id,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None,
                "registered": session.total_registered,
                "present": present_count,
                "attendance_rate": (present_count / session.total_registered * 100) if session.total_registered > 0 else 0
            }
            
            daily_summary["sessions"].append(session_data)
            total_registered += session.total_registered
            total_present += present_count
        
        daily_summary["total_students_registered"] = total_registered
        daily_summary["total_students_present"] = total_present
        daily_summary["overall_attendance_rate"] = (
            (total_present / total_registered * 100) if total_registered > 0 else 0
        )
        
        return daily_summary
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get daily attendance summary: {str(e)}"
        )


@router.get("/gate-entries/{date}")
async def get_daily_gate_entries(
    date: datetime,
    current_user: Annotated[dict, Depends(require_faculty_role)],
    attendance_service: Annotated[AttendanceService, Depends(get_attendance_service)]
):
    """
    Get all gate entries for a specific date.
    
    Requirements: 5.1, 5.2
    """
    try:
        # Create gate entry tracker
        gate_tracker = GateEntryTracker(attendance_service)
        
        # Get daily gate entries
        gate_entries = await gate_tracker.get_daily_gate_entries(date)
        
        return {
            "date": date.strftime("%Y-%m-%d"),
            "total_gate_entries": len(gate_entries),
            "gate_entries": gate_entries
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get daily gate entries: {str(e)}"
        )
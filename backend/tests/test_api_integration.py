"""
Integration tests for API services.

Requirements: 5.1, 5.2, 5.3
- Test REST API endpoints with various request scenarios
- Validate WebSocket communication and real-time updates
- Test API authentication and authorization mechanisms
"""

import pytest
import asyncio
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import status
import numpy as np
from PIL import Image
import io

from backend.api.main import create_app
from backend.api.websocket import connection_manager
from backend.models.student import StudentType
from backend.models.attendance import AttendanceStatus
from backend.core.config import Config


class TestAPIAuthentication:
    """Test API authentication and authorization mechanisms."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    def test_login_success(self, client):
        """Test successful login with valid credentials."""
        login_data = {
            "username": "faculty1",
            "password": "password123"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        assert data["user_info"]["username"] == "faculty1"
        assert data["user_info"]["role"] == "faculty"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        login_data = {
            "username": "invalid_user",
            "password": "wrong_password"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid username or password" in response.json()["detail"]
    
    def test_login_missing_fields(self, client):
        """Test login with missing required fields."""
        # Missing password
        response = client.post("/api/v1/auth/login", json={"username": "faculty1"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing username
        response = client.post("/api/v1/auth/login", json={"password": "password123"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without authentication token."""
        response = client.get("/api/v1/students/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/students/", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_protected_endpoint_with_valid_token(self, client):
        """Test accessing protected endpoint with valid token."""
        # First login to get token
        login_response = client.post("/api/v1/auth/login", json={
            "username": "faculty1",
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        
        # Use token to access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        with patch('backend.api.dependencies.get_student_repository') as mock_repo:
            mock_repo.return_value.get_students_with_filters = AsyncMock(return_value=[])
            response = client.get("/api/v1/students/", headers=headers)
            assert response.status_code == status.HTTP_200_OK
    
    def test_role_based_access_control(self, client):
        """Test role-based access control for admin endpoints."""
        # Login as faculty (non-admin)
        login_response = client.post("/api/v1/auth/login", json={
            "username": "faculty1",
            "password": "password123"
        })
        faculty_token = login_response.json()["access_token"]
        
        # Try to access admin endpoint
        headers = {"Authorization": f"Bearer {faculty_token}"}
        student_data = {
            "student_id": "STU001",
            "name": "Test Student",
            "student_type": "day_scholar",
            "email": "test@example.com"
        }
        
        with patch('backend.api.dependencies.get_student_repository'):
            response = client.post("/api/v1/students/", json=student_data, headers=headers)
            assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_token_refresh(self, client):
        """Test token refresh functionality."""
        # Login to get initial token
        login_response = client.post("/api/v1/auth/login", json={
            "username": "faculty1",
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        
        # Refresh token
        headers = {"Authorization": f"Bearer {token}"}
        response = client.post("/api/v1/auth/refresh", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_get_current_user_info(self, client):
        """Test getting current user information."""
        # Login to get token
        login_response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        
        # Get user info
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "admin"
        assert data["role"] == "admin"
        assert data["permissions"] == ["*"]

class
 TestStudentAPIEndpoints:
    """Test student management API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    @pytest.fixture
    def admin_headers(self, client):
        """Get admin authentication headers."""
        login_response = client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def faculty_headers(self, client):
        """Get faculty authentication headers."""
        login_response = client.post("/api/v1/auth/login", json={
            "username": "faculty1",
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_create_student_success(self, client, admin_headers):
        """Test successful student creation."""
        student_data = {
            "student_id": "STU001",
            "name": "John Doe",
            "student_type": "day_scholar",
            "email": "john.doe@example.com",
            "phone": "+1234567890",
            "class_id": "CS101"
        }
        
        with patch('backend.api.dependencies.get_student_repository') as mock_repo:
            mock_repo.return_value.get_student_by_id = AsyncMock(return_value=None)
            mock_repo.return_value.create_student = AsyncMock(return_value=Mock(
                student_id="STU001",
                name="John Doe",
                student_type=StudentType.DAY_SCHOLAR,
                enrollment_date=datetime.utcnow(),
                is_active=True,
                email="john.doe@example.com",
                phone="+1234567890",
                class_id="CS101"
            ))
            
            response = client.post("/api/v1/students/", json=student_data, headers=admin_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["student_id"] == "STU001"
            assert data["name"] == "John Doe"
            assert data["student_type"] == "day_scholar"
    
    def test_create_student_duplicate(self, client, admin_headers):
        """Test creating duplicate student."""
        student_data = {
            "student_id": "STU001",
            "name": "John Doe",
            "student_type": "day_scholar"
        }
        
        with patch('backend.api.dependencies.get_student_repository') as mock_repo:
            mock_repo.return_value.get_student_by_id = AsyncMock(return_value=Mock(student_id="STU001"))
            
            response = client.post("/api/v1/students/", json=student_data, headers=admin_headers)
            
            assert response.status_code == status.HTTP_409_CONFLICT
            assert "already exists" in response.json()["detail"]
    
    def test_get_students_with_filters(self, client, faculty_headers):
        """Test getting students with various filters."""
        mock_students = [
            Mock(
                student_id="STU001",
                name="John Doe",
                student_type=StudentType.DAY_SCHOLAR,
                enrollment_date=datetime.utcnow(),
                is_active=True,
                email="john@example.com",
                phone="+1234567890",
                class_id="CS101"
            )
        ]
        
        with patch('backend.api.dependencies.get_student_repository') as mock_repo:
            mock_repo.return_value.get_students_with_filters = AsyncMock(return_value=mock_students)
            
            # Test with filters
            response = client.get(
                "/api/v1/students/?class_id=CS101&student_type=day_scholar&is_active=true",
                headers=faculty_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["student_id"] == "STU001"
    
    def test_get_student_by_id(self, client, faculty_headers):
        """Test getting student by ID."""
        mock_student = Mock(
            student_id="STU001",
            name="John Doe",
            student_type=StudentType.DAY_SCHOLAR,
            enrollment_date=datetime.utcnow(),
            is_active=True,
            email="john@example.com",
            phone="+1234567890",
            class_id="CS101"
        )
        
        with patch('backend.api.dependencies.get_student_repository') as mock_repo:
            mock_repo.return_value.get_student_by_id = AsyncMock(return_value=mock_student)
            
            response = client.get("/api/v1/students/STU001", headers=faculty_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["student_id"] == "STU001"
            assert data["name"] == "John Doe"
    
    def test_get_student_not_found(self, client, faculty_headers):
        """Test getting non-existent student."""
        with patch('backend.api.dependencies.get_student_repository') as mock_repo:
            mock_repo.return_value.get_student_by_id = AsyncMock(return_value=None)
            
            response = client.get("/api/v1/students/NONEXISTENT", headers=faculty_headers)
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_register_face_success(self, client, admin_headers):
        """Test successful face registration."""
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='red')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='JPEG')
        img_data = base64.b64encode(img_buffer.getvalue()).decode()
        
        face_data = {
            "student_id": "STU001",
            "image_data": img_data
        }
        
        mock_student = Mock(student_id="STU001")
        mock_detection = Mock(
            bounding_box=(10, 10, 90, 90),
            liveness_score=0.8
        )
        
        with patch('backend.api.dependencies.get_student_repository') as mock_repo, \
             patch('backend.api.dependencies.get_face_recognition_service') as mock_face_service, \
             patch('backend.core.encryption.encrypt_data') as mock_encrypt:
            
            mock_repo.return_value.get_student_by_id = AsyncMock(return_value=mock_student)
            mock_repo.return_value.update_student = AsyncMock(return_value=None)
            mock_face_service.return_value.detect_faces = Mock(return_value=[mock_detection])
            mock_face_service.return_value.extract_embedding = Mock(return_value=np.random.rand(512))
            mock_encrypt.return_value = b"encrypted_embedding"
            
            response = client.post("/api/v1/students/STU001/register-face", json=face_data, headers=admin_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "Face registered successfully" in data["message"]
class T
estSessionAPIEndpoints:
    """Test session management API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    @pytest.fixture
    def faculty_headers(self, client):
        """Get faculty authentication headers."""
        login_response = client.post("/api/v1/auth/login", json={
            "username": "faculty1",
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_create_session_success(self, client, faculty_headers):
        """Test successful session creation."""
        session_data = {
            "class_id": "CS101",
            "faculty_id": "FAC001"
        }
        
        mock_session = Mock(
            session_id="SES001",
            class_id="CS101",
            faculty_id="FAC001",
            start_time=datetime.utcnow(),
            end_time=None,
            total_registered=30,
            total_detected=0,
            is_active=True
        )
        
        with patch('backend.api.dependencies.get_attendance_service') as mock_service:
            mock_processor = Mock()
            mock_processor.start_classroom_session = AsyncMock(return_value="SES001")
            mock_service.return_value.attendance_repo.get_session_by_id = AsyncMock(return_value=mock_session)
            
            with patch('backend.services.attendance_service.ClassroomAttendanceProcessor', return_value=mock_processor):
                response = client.post("/api/v1/sessions/", json=session_data, headers=faculty_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["session_id"] == "SES001"
                assert data["class_id"] == "CS101"
                assert data["is_active"] is True
    
    def test_get_sessions_with_filters(self, client, faculty_headers):
        """Test getting sessions with filters."""
        mock_sessions = [
            Mock(
                session_id="SES001",
                class_id="CS101",
                faculty_id="FAC001",
                start_time=datetime.utcnow(),
                end_time=None,
                total_registered=30,
                total_detected=25,
                is_active=True
            )
        ]
        
        with patch('backend.api.dependencies.get_attendance_service') as mock_service:
            mock_service.return_value.attendance_repo.get_sessions_with_filters = AsyncMock(return_value=mock_sessions)
            
            response = client.get(
                "/api/v1/sessions/?class_id=CS101&is_active=true",
                headers=faculty_headers
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data) == 1
            assert data[0]["session_id"] == "SES001"
    
    def test_end_session(self, client, faculty_headers):
        """Test ending an active session."""
        with patch('backend.api.dependencies.get_attendance_service') as mock_service:
            mock_processor = Mock()
            mock_processor.end_classroom_session = AsyncMock(return_value=True)
            
            with patch('backend.services.attendance_service.ClassroomAttendanceProcessor', return_value=mock_processor):
                response = client.post("/api/v1/sessions/SES001/end", headers=faculty_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "ended successfully" in data["message"]
    
    def test_get_real_time_attendance(self, client, faculty_headers):
        """Test getting real-time attendance data."""
        mock_attendance_data = {
            'session_id': 'SES001',
            'class_id': 'CS101',
            'total_registered': 30,
            'total_present': 25,
            'total_absent': 5,
            'attendance_percentage': 83.33,
            'present_students': [{'student_id': 'STU001', 'name': 'John Doe'}],
            'absent_students': [{'student_id': 'STU002', 'name': 'Jane Smith'}],
            'session_start': datetime.utcnow().isoformat(),
            'is_active': True
        }
        
        with patch('backend.api.dependencies.get_attendance_service') as mock_service:
            mock_processor = Mock()
            mock_processor.get_real_time_attendance = AsyncMock(return_value=mock_attendance_data)
            
            with patch('backend.services.attendance_service.ClassroomAttendanceProcessor', return_value=mock_processor):
                response = client.get("/api/v1/sessions/SES001/real-time", headers=faculty_headers)
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["session_id"] == "SES001"
                assert data["total_registered"] == 30
                assert data["attendance_percentage"] == 83.33


class TestAttendanceAPIEndpoints:
    """Test attendance management API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    @pytest.fixture
    def faculty_headers(self, client):
        """Get faculty authentication headers."""
        login_response = client.post("/api/v1/auth/login", json={
            "username": "faculty1",
            "password": "password123"
        })
        token = login_response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_record_gate_entry(self, client, faculty_headers):
        """Test recording gate entry."""
        gate_entry_data = {
            "student_id": "STU001",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        with patch('backend.api.dependencies.get_attendance_service') as mock_service:
            mock_service.return_value.record_gate_entry = AsyncMock(return_value=True)
            
            response = client.post("/api/v1/attendance/gate-entry", json=gate_entry_data, headers=faculty_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "Gate entry recorded successfully" in data["message"]
            assert data["student_id"] == "STU001"
    
    def test_mark_classroom_attendance(self, client, faculty_headers):
        """Test marking classroom attendance."""
        classroom_data = {
            "session_id": "SES001",
            "detections": [
                {
                    "bounding_box": [10, 10, 90, 90],
                    "confidence": 0.95,
                    "embedding": [0.1] * 512,
                    "liveness_score": 0.8
                }
            ]
        }
        
        mock_session = Mock(
            session_id="SES001",
            total_detected=1,
            total_registered=30
        )
        
        with patch('backend.api.dependencies.get_attendance_service') as mock_service:
            mock_service.return_value.mark_classroom_attendance = AsyncMock(return_value=mock_session)
            
            response = client.post("/api/v1/attendance/classroom", json=classroom_data, headers=faculty_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "Classroom attendance marked successfully" in data["message"]
            assert data["session_id"] == "SES001"
    
    def test_generate_attendance_report(self, client, faculty_headers):
        """Test generating attendance report."""
        report_request = {
            "session_id": "SES001",
            "include_emotions": True,
            "include_cross_verification": True
        }
        
        mock_report_data = {
            'session_info': {'session_id': 'SES001', 'class_id': 'CS101'},
            'overall_statistics': {'total_registered': 30, 'total_present': 25},
            'day_scholar_report': {'total': 20, 'present': 18},
            'hostel_student_report': {'total': 10, 'present': 7},
            'alerts': ['5 students missing'],
            'generated_at': datetime.utcnow().isoformat()
        }
        
        with patch('backend.api.dependencies.get_attendance_service') as mock_service:
            mock_service.return_value.generate_attendance_report = AsyncMock(return_value=mock_report_data)
            
            response = client.post("/api/v1/attendance/report", json=report_request, headers=faculty_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["session_info"]["session_id"] == "SES001"
            assert data["overall_statistics"]["total_registered"] == 30
    
    def test_validate_attendance(self, client, faculty_headers):
        """Test attendance validation."""
        validation_request = {
            "session_id": "SES001"
        }
        
        mock_session = Mock(
            session_id="SES001",
            total_registered=30,
            total_detected=25
        )
        
        mock_validation_result = {
            'status': 'warning',
            'alerts': ['5 students missing']
        }
        
        mock_missing_students = [
            Mock(student_id="STU001", name="John Doe", student_type=StudentType.DAY_SCHOLAR)
        ]
        
        with patch('backend.api.dependencies.get_validation_service') as mock_validation_service:
            mock_validation_service.return_value.attendance_service.attendance_repo.get_session_by_id = AsyncMock(return_value=mock_session)
            mock_validation_service.return_value.validate_attendance_count = AsyncMock(return_value=mock_validation_result)
            mock_validation_service.return_value.check_missing_students = AsyncMock(return_value=mock_missing_students)
            
            response = client.post("/api/v1/attendance/validate", json=validation_request, headers=faculty_headers)
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["session_id"] == "SES001"
            assert data["validation_status"] == "warning"
            assert len(data["missing_students"]) == 1
@pyte
st.mark.asyncio
class TestWebSocketIntegration:
    """Test WebSocket communication and real-time updates."""
    
    @pytest.fixture
    def mock_websocket_app(self):
        """Create mock WebSocket application."""
        app = create_app()
        return app
    
    async def test_websocket_connection_establishment(self):
        """Test WebSocket connection establishment."""
        connection_id = "test-connection-1"
        user_info = {"user_id": "faculty1", "role": "faculty"}
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Test connection
        await connection_manager.connect(mock_websocket, connection_id, user_info)
        
        # Verify connection was established
        assert connection_id in connection_manager.active_connections
        assert connection_manager.connection_metadata[connection_id]["user_info"] == user_info
        mock_websocket.accept.assert_called_once()
    
    async def test_websocket_message_handling(self):
        """Test WebSocket message handling."""
        connection_id = "test-connection-2"
        user_info = {"user_id": "faculty1", "role": "faculty"}
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Establish connection
        await connection_manager.connect(mock_websocket, connection_id, user_info)
        
        # Test ping message
        await connection_manager.send_personal_message(connection_id, {
            "type": "ping"
        })
        
        # Verify message was sent
        mock_websocket.send_text.assert_called()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "ping"
    
    async def test_session_subscription(self):
        """Test session subscription functionality."""
        connection_id = "test-connection-3"
        session_id = "SES001"
        user_info = {"user_id": "faculty1", "role": "faculty"}
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Establish connection
        await connection_manager.connect(mock_websocket, connection_id, user_info)
        
        # Subscribe to session
        await connection_manager.subscribe_to_session(connection_id, session_id)
        
        # Verify subscription
        assert session_id in connection_manager.session_subscriptions
        assert connection_id in connection_manager.session_subscriptions[session_id]
        assert session_id in connection_manager.connection_metadata[connection_id]["subscriptions"]
    
    async def test_attendance_update_broadcast(self):
        """Test broadcasting attendance updates."""
        connection_id = "test-connection-4"
        session_id = "SES001"
        user_info = {"user_id": "faculty1", "role": "faculty"}
        
        # Mock WebSocket
        mock_websocket = AsyncMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.send_text = AsyncMock()
        
        # Establish connection and subscribe
        await connection_manager.connect(mock_websocket, connection_id, user_info)
        await connection_manager.subscribe_to_session(connection_id, session_id)
        
        # Broadcast attendance update
        attendance_data = {
            "total_present": 25,
            "total_registered": 30,
            "attendance_percentage": 83.33
        }
        
        await connection_manager.send_attendance_update(session_id, attendance_data)
        
        # Verify broadcast was sent"])e__, "-v_filin([_st.ma   pyte":
 "__main__ __ ==if __nameROR


SERVER_ERNAL_500_INTERTP_.HT status_code ==e.statusspons   assert re)
         ty_headersfacul, headers=    }"
        01"FAC0 id":"faculty_                S101",
id": "Css_  "cla           json={
   ", s//v1/session("/apiclient.postse =    respon            
  )
       able"ice unavailrv"Seception(effect = Exe.side_mock_servic            service:
') as mock_rvicendance_ses.get_atteiedencapi.depenh('backend.  with patc   
   s."""le errorce unavailabg of servihandlin"""Test        
 ders):faculty_heant, f, clieror(sellable_ernavairvice_u def test_se
   
    ORERVER_ERRERNAL_SHTTP_500_INTtus.status_code == se.staresponassert            headers)
 culty_ders=fa", heatudents//v1/sget("/api client.e =   respons              
            )
 ")
       failede connection("Databasionfect=Except  side_ef           k(
   cMocsynrs = Alteh_fi_wittudents_value.get_so.return    mock_rep       
 _repo:ry') as mockt_repositot_studengecies.api.dependenkend.atch('bacith p   w"""
     on errors.ti connecbase of data handling""Test   "rs):
     headey_cultt, faself, clien_error(onnection_cabase_dat    def testITY
    
BLE_ENTUNPROCESSAus.HTTP_422_de == statse.status_co respon  assert
          y_headers)acult, headers=f_data=incompletents/", json/stude"/api/v1ient.post(= cl  response     :
      y')repositordent_tu.get_sesenci.dependkend.apibac('tchh pa      wit        
      }
"
    olar: "day_scht_type""studen        
    nt",st Stude": "Te    "name      ta = {
  dae_ncomplet i
       ldt_id fie studen required# Missing      ""
  fields." required  missingg ofest handlin""T  "rs):
      ulty_headefacclient, lf, ed_fields(seg_requirst_missin  def te
    
  TYESSABLE_ENTIROCNP_UHTTP_422s.atust_code == statusonse. assert resp   
          )
  "}on/jsonicati": "applontent-Type"C, _headerscultyders={**fa      hea
      n","invalid jsota=        da   dents/",
 api/v1/stu  "/      post(
    = client.ponse    res  """
   ts.esequalid JSON rf invhandling o"Test       "":
  lty_headers), facuientf, clrequest(seln__invalid_jsoef test    d   
}
 {token}" f"Bearer n":thorizatioAun {"       returken"]
 "access_tonse.json()[gin_respo token = lo      })
        
 d123""passwor": assword       "p,
     y1""faculte": ernam"us           ", json={
 /auth/loginpi/v1t("/a client.possponse =in_re     log"""
   ders.tication heaty authenGet facul      """ient):
   cl(self,ty_headers faculdef
    turefixt.ytes    @ppp)
    
(aestClient Tturn     re)
    create_app(     app =."""
   lient test c"Create ""    ):
   client(selfef re
    dst.fixtuyte   @p   
 "
 rios.""ling scena error handPI A  """Testandling:
  rorHErestAPI

class Tn_id]
ns[sessiocriptiobs.session_sun_managern connectio not inection_idt conasser           s:
 ionscriptubion_s.sessanagerconnection_mn _id ision      if seseanup
   clriptionubscion s sessrify Ve        #    
   eat
 last_heartb_manager.iononnect in c notonnection_id  assert c    ta
  ion_metadaager.connectction_man conne_id not inctionne conrt     asseons
   ectiactive_connanager.nection_mot in connection_id nt conser as  up
     ify clean    # Ver     
    _id)
   ionnectonnect(cconr.dismanagen_ctioit conne   awa  connect
         # Dis     
  _id]
   sions[sesionbscriptession_su_manager.sonecticonnd in n_iconnectioert      asss
   nectionr.active_conon_managein connectinnection_id  assert co
       ion existsectfy conn # Veri         
 
     on_id), sessiection_idssion(connbe_to_sebscrier.su_managtionnecwait con        a)
 user_infonection_id,socket, con_webocker.connect(mn_managnectioait con aw       cribe
d subson annnectih cois# Establ
               yncMock()
 ext = As_tsocket.send   mock_web  ock()
   t = AsyncMaccepwebsocket.mock_      ck()
  syncMoket = Asoceb mock_w      Socket
  Mock Web #  
           y"}
   "facult":, "rolety1"": "facul {"user_ider_info =
        usES001"n_id = "S  sessio"
      ection-7est-conn = "tction_id      conne  """
ect.isconnp on deanu clectionest conn    """T):
    leanup(selfonnection_cf test_c  async de  
    ssage"]
["mege["data"]messain sent_g" missin assert ""
       rning== "waty"] ria"]["seveatge["dsent_messa   assert 
      "alert"ype"] ==sage["tmest_assert sen  
      s[0][0])l_argalsend_text.ck_websocket.ds(mocon.loaage = js  sent_mess      t_called()
xt.assertecket.send_soeb    mock_w   sent
 alert was  Verify         #        
)
session_idta, _dart(alertr.send_aleon_managenectiawait con             
   
        }
 5ng_count":si  "mis
          nce",tenda from atsingents mis"5 studmessage":    ",
         ing"arnerity": "w   "sev         t_data = {
ler art
       leBroadcast a  #  
             _id)
_id, sessionionsion(connecto_sesbscribe_tanager.sunnection_mcowait )
        a, user_infoidion_, connectsocketebock_wconnect(mnager.ion_maonnectait c     aw
   iben and subscr connectiolish  # Estab  
    ()
         = AsyncMocksend_text_websocket.mock   ()
     ockept = AsyncMaccsocket.k_web       moccMock()
 synsocket = A mock_web
        WebSocket # Mock            
  y"}
 faculte": ""rolulty1", : "facid"= {"user_fo user_in     001"
   id = "SES session_      "
 nnection-6est-cod = "tnnection_i  co"
      "lerts."ng aroadcastiTest b"""  
      self):st(rt_broadcaef test_aleasync d
    
    0.72== "] oret_sc"engagemen][data""ent_message[ assert s    id
   sion_= sesid"] =sion_"ses_message[ssert sent  a  "
    pdatemotion_u"e"type"] == message[rt sent_sse
        a0])all_args[0][t.cd_texsent.bsockeock_weads(m.loge = jsonsames      sent_d()
  _calleext.assertocket.send_tck_webs
        mo sentasoadcast w # Verify br          
   ata)
  on_dd, emotission_i_update(seemotionanager.send__mt connection      awai
  
              }
  : 0.72nt_score"ageme "eng     5.0,
      onfused": 1        "c  25.0,
  red":  "bo    
       0,sted": 60. "intere           {
= _data      emotion   te
dation updcast emo Broa
        #      sion_id)
  , sesnnection_idion(co_to_sessr.subscribeon_manageonnecti  await c)
      user_info_id, , connectionwebsocketect(mock_ager.connection_mant conn        awai subscribe
ction and connesh # Establi         
      Mock()
ext = Asyncet.send_tmock_websock    Mock()
    t = Asyncocket.accepmock_webs      ock()
  = AsyncMbsocket      mock_we   ebSocket
ck W     # Mo       
   ty"}
  "facul"role":", : "faculty1id"= {"user_o  user_inf
       "SES001"ion_id =        sess
 "nection-5t-con "tesion_id =ect    conn""
    updates."istics ion statsting emotst broadca""Te     "self):
   st(_broadcaate_emotion_upd def test 
    async== 25
   resent"] tal_p"to["data"]sage[ sent_mesert   ass   sion_id
  ses_id"] == essionsage["ses_massert sent"
        nce_update"attenda == "type"]_message[sert sent  as[0])
      rgs[0]t.call_at.send_texbsockeoads(mock_wege = json.lsent_messa  
      alled().assert_c.send_textcketmock_webso
        
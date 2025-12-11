# SMART ATTENDANCE SYSTEM - QUICK START GUIDE

## 🎉 System is Running!

All services are operational. Access the system at:
- **Frontend Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **API Base URL**: http://localhost:8000/api/v1

---

## 🔧 FIXES APPLIED

### 1. Session Auto-Restart Issue - FIXED ✅
**Problem**: Session was restarting automatically after ending
**Solution**: 
- Disabled mock data mode in frontend
- Updated session hook to properly clear session when null
- Frontend now uses real backend API

**Note**: The backend needs the `/attendance/current-session` endpoint. For now, the system will work but you may see errors in the console until this endpoint is implemented.

---

## 👥 STUDENT REGISTRATION

### Method 1: Using Postman (Recommended for Now)

#### Step 1: Get Authentication Token
```http
POST http://localhost:8000/api/v1/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

#### Step 2: Register Student
```http
POST http://localhost:8000/api/v1/students/
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: application/json

{
  "student_id": "STU001",
  "name": "John Doe",
  "student_type": "day_scholar",
  "email": "john.doe@example.com",
  "phone": "+1234567890",
  "class_id": "CS101"
}
```

#### Step 3: Register Face (Optional)
```http
POST http://localhost:8000/api/v1/students/STU001/register-face
Authorization: Bearer YOUR_TOKEN_HERE
Content-Type: application/json

{
  "student_id": "STU001",
  "image_data": "BASE64_ENCODED_IMAGE_HERE"
}
```

**To get base64 image**:
1. Take a photo of the student
2. Use an online tool like https://www.base64-image.de/ to convert to base64
3. Copy the base64 string (without the `data:image/jpeg;base64,` prefix)

### Method 2: Using Frontend (Requires Implementation)

The frontend currently doesn't have a student registration page. This would need to be added with:
- Student registration form
- Camera component for face capture
- Integration with backend API

---

## 📷 CAMERA ACCESS ISSUE

### Why Camera Isn't Opening:

1. **No Camera Component**: The current frontend doesn't have a camera capture component for attendance
2. **Backend Integration**: The system is designed to work with physical cameras at gate/classroom, not browser webcam
3. **Architecture**: The system expects:
   - Physical cameras connected to the backend
   - Backend processes video streams
   - Frontend displays results

### Current Workflow:

The system is designed for:
```
Physical Camera → Backend Processing → Face Recognition → Frontend Display
```

Not:
```
Browser Webcam → Frontend → Backend
```

### To Use Browser Webcam (Requires Development):

You would need to add:
1. **Frontend**: Camera component using `navigator.mediaDevices.getUserMedia()`
2. **Frontend**: Capture photo and send to backend
3. **Backend**: API endpoint to receive and process photos
4. **Integration**: Connect frontend camera to attendance marking

---

## 🚀 CURRENT WORKING FEATURES

✅ **Dashboard**: View attendance statistics
✅ **Session Management**: Start/End sessions (now fixed!)
✅ **API**: All backend services running
✅ **Database**: PostgreSQL and Redis operational
✅ **Student API**: Register students via Postman
✅ **Real-time Updates**: WebSocket integration

---

## ⚠️ FEATURES THAT NEED IMPLEMENTATION

❌ **Frontend Student Registration**: No UI for adding students
❌ **Browser Camera Integration**: No webcam capture component
❌ **Current Session Endpoint**: Backend API endpoint missing
❌ **Face Registration UI**: No interface for capturing student photos
❌ **Live Camera Feed**: No real-time video display

---

## 📝 RECOMMENDED NEXT STEPS

### For Testing Right Now:

1. **Register Students via Postman**
   - Use the API endpoints above
   - Register 5-10 test students
   - Skip face registration for now (optional)

2. **Test Session Management**
   - Go to http://localhost:3000
   - Click "Start Session"
   - Enter class ID (e.g., "CS101")
   - Session should start
   - Click "End Session" - it should end and NOT restart

3. **View Dashboard**
   - See attendance statistics
   - View student lists
   - Check real-time updates

### For Full Functionality:

You would need to implement:
1. **Student Registration Page** in frontend
2. **Camera Capture Component** for browser webcam
3. **Missing Backend Endpoints**:
   - `/attendance/current-session`
   - `/attendance/capture-photo` (for browser webcam)
4. **Face Registration Flow** in frontend

---

## 🐛 TROUBLESHOOTING

### Session Still Auto-Restarting?
- Clear browser cache and reload
- Check browser console for errors
- Verify `USE_MOCK_DATA` is false in `frontend/src/services/api.ts`

### Can't Register Students?
- Ensure backend is running: `docker ps`
- Check API is accessible: http://localhost:8000/docs
- Verify authentication token is valid

### Camera Not Working?
- This is expected - camera integration needs to be built
- Use Postman to register students for now
- Consider adding webcam component if needed

---

## 📞 SUPPORT

If you encounter issues:
1. Check Docker containers: `docker ps`
2. Check API logs: `docker logs api_gateway`
3. Check frontend console in browser DevTools
4. Verify all services are healthy

---

**Last Updated**: November 22, 2025
**System Status**: ✅ Operational (with noted limitations)

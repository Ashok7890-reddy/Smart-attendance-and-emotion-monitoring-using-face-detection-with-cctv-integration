# HOW TO USE THE SMART ATTENDANCE SYSTEM

## 📚 TABLE OF CONTENTS
1. [How to Register New Students](#how-to-register-new-students)
2. [How to Take Attendance](#how-to-take-attendance)
3. [Troubleshooting](#troubleshooting)

---

## 👥 HOW TO REGISTER NEW STUDENTS

Currently, the system doesn't have a student registration UI in the frontend. You need to use **Postman** or any API client to register students.

### Method 1: Using Postman (Recommended)

#### Step 1: Get Authentication Token

1. **Open Postman**
2. **Create a new POST request**
3. **URL**: `http://localhost:8000/api/v1/auth/login`
4. **Headers**: 
   - `Content-Type: application/json`
5. **Body** (select "raw" and "JSON"):
```json
{
  "username": "admin",
  "password": "admin123"
}
```
6. **Click Send**
7. **Copy the `access_token`** from the response

**Response Example:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

---

#### Step 2: Register a New Student

1. **Create a new POST request**
2. **URL**: `http://localhost:8000/api/v1/students/`
3. **Headers**:
   - `Content-Type: application/json`
   - `Authorization: Bearer YOUR_ACCESS_TOKEN_HERE` (paste the token from Step 1)
4. **Body** (select "raw" and "JSON"):

**For Day Scholar:**
```json
{
  "student_id": "99220041951",
  "name": "New Student Name",
  "student_type": "day_scholar",
  "email": "student@example.com",
  "phone": "+91-9876543210",
  "class_id": "CS101"
}
```

**For Hostel Student:**
```json
{
  "student_id": "99220041952",
  "name": "Another Student",
  "student_type": "hostel_student",
  "email": "student2@example.com",
  "phone": "+91-9876543211",
  "class_id": "CS101"
}
```

5. **Click Send**

**Success Response:**
```json
{
  "student_id": "99220041951",
  "name": "New Student Name",
  "student_type": "day_scholar",
  "enrollment_date": "2025-11-22T10:30:00Z",
  "is_active": true,
  "email": "student@example.com",
  "phone": "+91-9876543210",
  "class_id": "CS101"
}
```

---

#### Step 3: Register Student's Face (Optional but Recommended)

1. **Take a clear photo** of the student's face
2. **Convert the photo to Base64**:
   - Use online tool: https://www.base64-image.de/
   - Or use command line: `base64 photo.jpg`
   - Copy the base64 string (without the `data:image/jpeg;base64,` prefix if present)

3. **Create a new POST request**
4. **URL**: `http://localhost:8000/api/v1/students/99220041951/register-face`
5. **Headers**:
   - `Content-Type: application/json`
   - `Authorization: Bearer YOUR_ACCESS_TOKEN_HERE`
6. **Body**:
```json
{
  "student_id": "99220041951",
  "image_data": "YOUR_BASE64_IMAGE_STRING_HERE"
}
```

7. **Click Send**

**Success Response:**
```json
{
  "message": "Face registered successfully for student 99220041951",
  "embedding_size": 512,
  "liveness_score": 0.85
}
```

---

### Method 2: Using cURL (Command Line)

**Register Student:**
```bash
curl -X POST "http://localhost:8000/api/v1/students/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "student_id": "99220041951",
    "name": "New Student",
    "student_type": "day_scholar",
    "email": "student@example.com",
    "class_id": "CS101"
  }'
```

---

### Bulk Registration (Multiple Students at Once)

**URL**: `http://localhost:8000/api/v1/students/bulk`
**Method**: POST
**Body**:
```json
{
  "students": [
    {
      "student_id": "99220041951",
      "name": "Student One",
      "student_type": "day_scholar",
      "email": "student1@example.com",
      "class_id": "CS101"
    },
    {
      "student_id": "99220041952",
      "name": "Student Two",
      "student_type": "hostel_student",
      "email": "student2@example.com",
      "class_id": "CS101"
    }
  ]
}
```

---

## 📸 HOW TO TAKE ATTENDANCE

### Current System Architecture

The Smart Attendance System is designed to work with **physical cameras** connected to the backend, not browser webcams. Here's how it works:

```
Physical Camera → Backend Processing → Face Recognition → Dashboard Display
```

### Option 1: Using Physical Cameras (Production Setup)

**For Day Scholars:**
1. **Gate Camera** captures face when student enters campus
2. **Classroom Camera** captures face when student enters classroom
3. System cross-verifies both entries
4. Marks attendance as complete

**For Hostel Students:**
1. **Classroom Camera** captures face when student enters
2. Marks attendance immediately (no gate entry needed)

**Setup Required:**
- Physical cameras at gate and classroom
- Cameras connected to backend server
- Backend configured with camera IDs

---

### Option 2: Manual Attendance (Current Workaround)

Since physical cameras aren't set up yet, you can manually mark attendance using the API:

#### Step 1: Start an Attendance Session

**In the Dashboard:**
1. Go to http://localhost:3000
2. Enter **Class ID** (e.g., "CS101")
3. Click **"Start Session"**
4. Note the session ID from the response

**Or via API:**
```http
POST http://localhost:8000/api/v1/sessions/start
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "class_id": "CS101",
  "faculty_id": "faculty-001"
}
```

---

#### Step 2: Mark Gate Entry (For Day Scholars)

**URL**: `http://localhost:8000/api/v1/attendance/gate-entry`
**Method**: POST
**Headers**: Authorization Bearer token
**Body**:
```json
{
  "student_id": "99220041944",
  "timestamp": "2025-11-22T09:15:00Z"
}
```

**Repeat for each day scholar entering the gate.**

---

#### Step 3: Mark Classroom Attendance

**URL**: `http://localhost:8000/api/v1/attendance/classroom`
**Method**: POST
**Headers**: Authorization Bearer token
**Body**:
```json
{
  "session_id": "session-001",
  "detections": [
    {
      "student_id": "99220041944",
      "confidence": 0.95,
      "bounding_box": [100, 100, 200, 200],
      "timestamp": "2025-11-22T09:30:00Z"
    },
    {
      "student_id": "99220041945",
      "confidence": 0.92,
      "bounding_box": [150, 150, 250, 250],
      "timestamp": "2025-11-22T09:30:00Z"
    }
  ]
}
```

---

#### Step 4: View Attendance

**In the Dashboard:**
1. Go to http://localhost:3000
2. You'll see:
   - Total students registered
   - Students present
   - Students absent
   - Attendance percentage
   - List of all students with their status

**Or via API:**
```http
GET http://localhost:8000/api/v1/attendance/session/{session_id}/records
Authorization: Bearer YOUR_TOKEN
```

---

#### Step 5: End Session

**In the Dashboard:**
1. Click **"End Session"** button
2. Confirm when prompted
3. Session will end and attendance will be finalized

**Or via API:**
```http
POST http://localhost:8000/api/v1/sessions/{session_id}/end
Authorization: Bearer YOUR_TOKEN
```

---

### Option 3: Browser Webcam Integration (Needs Development)

To use your computer's webcam for attendance, you would need to add:

1. **Frontend Camera Component**:
   - Capture photo from webcam
   - Send to backend for processing

2. **Backend Photo Processing Endpoint**:
   - Receive photo from frontend
   - Perform face recognition
   - Mark attendance

**This feature is not currently implemented but can be added if needed.**

---

## 🎯 COMPLETE ATTENDANCE WORKFLOW EXAMPLE

### Scenario: Taking Attendance for CS101 Class

**Step 1: Start Session**
- Dashboard → Enter "CS101" → Click "Start Session"
- Session starts, you see "Session Active"

**Step 2: Students Enter**
- Day scholars enter through gate (gate entry recorded)
- All students enter classroom (classroom entry recorded)

**Step 3: View Real-time Updates**
- Dashboard shows students as they're detected
- Attendance percentage updates automatically
- Missing students are highlighted

**Step 4: End Session**
- Click "End Session" → Confirm
- Final attendance is saved
- Reports can be generated

---

## 🔍 TROUBLESHOOTING

### "Cannot register student - 401 Unauthorized"
**Solution**: Your authentication token expired. Get a new token from Step 1.

### "Student already exists"
**Solution**: Use a different student_id or update the existing student using PUT request.

### "Face registration failed - No face detected"
**Solution**: 
- Ensure the photo has a clear, visible face
- Photo should be well-lit
- Only one face should be in the photo
- Try a different photo

### "Session not starting"
**Solution**:
- Check if another session is already active
- End the current session first
- Refresh the dashboard

### "Students not showing in dashboard"
**Solution**:
- Ensure students are registered in the same class_id
- Check if session is active
- Refresh the browser

---

## 📊 QUICK REFERENCE

### Student Types
- **day_scholar**: Requires gate entry + classroom entry
- **hostel_student**: Requires only classroom entry

### API Endpoints
- **Login**: `POST /api/v1/auth/login`
- **Register Student**: `POST /api/v1/students/`
- **Register Face**: `POST /api/v1/students/{id}/register-face`
- **Start Session**: `POST /api/v1/sessions/start`
- **Gate Entry**: `POST /api/v1/attendance/gate-entry`
- **Classroom**: `POST /api/v1/attendance/classroom`
- **End Session**: `POST /api/v1/sessions/{id}/end`

### Dashboard URLs
- **Main Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health

---

## 💡 TIPS

1. **Always get a fresh token** before making API calls
2. **Use consistent class_id** for all students in the same class
3. **Register faces** for better attendance accuracy
4. **End sessions** properly to save attendance data
5. **Check API docs** at http://localhost:8000/docs for more endpoints

---

## 🆘 NEED HELP?

1. Check the **QUICK_START_GUIDE.md** for system overview
2. Check **STUDENT_DATA.md** for mock student information
3. View API documentation at http://localhost:8000/docs
4. Check Docker logs: `docker logs api_gateway`

---

**Last Updated**: November 22, 2025
**System Version**: 1.0.0

# POSTMAN COLLECTION GUIDE

## 🚀 Quick Setup for Student Registration & Attendance

This guide will help you set up Postman to easily register students and take attendance.

---

## 📦 POSTMAN COLLECTION SETUP

### Step 1: Create a New Collection

1. Open Postman
2. Click "New" → "Collection"
3. Name it: "Smart Attendance System"
4. Save

---

### Step 2: Set Up Environment Variables

1. Click on "Environments" (left sidebar)
2. Click "+" to create new environment
3. Name it: "Smart Attendance - Local"
4. Add these variables:

| Variable | Initial Value | Current Value |
|----------|---------------|---------------|
| `base_url` | `http://localhost:8000/api/v1` | `http://localhost:8000/api/v1` |
| `token` | (leave empty) | (will be set after login) |

5. Save and select this environment

---

## 🔐 REQUEST 1: LOGIN

**Name**: Login
**Method**: POST
**URL**: `{{base_url}}/auth/login`

**Headers**:
```
Content-Type: application/json
```

**Body** (raw JSON):
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Tests** (to auto-save token):
```javascript
if (pm.response.code === 200) {
    var jsonData = pm.response.json();
    pm.environment.set("token", jsonData.access_token);
    console.log("Token saved:", jsonData.access_token);
}
```

**Click Send** → Token will be automatically saved to environment!

---

## 👤 REQUEST 2: REGISTER STUDENT

**Name**: Register Student
**Method**: POST
**URL**: `{{base_url}}/students/`

**Headers**:
```
Content-Type: application/json
Authorization: Bearer {{token}}
```

**Body** (raw JSON):
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

**To register multiple students**: Just change the values and click Send again!

---

## 📸 REQUEST 3: REGISTER FACE

**Name**: Register Face
**Method**: POST
**URL**: `{{base_url}}/students/99220041951/register-face`

**Headers**:
```
Content-Type: application/json
Authorization: Bearer {{token}}
```

**Body** (raw JSON):
```json
{
  "student_id": "99220041951",
  "image_data": "PASTE_BASE64_IMAGE_HERE"
}
```

**How to get Base64 image**:
1. Go to https://www.base64-image.de/
2. Upload student photo
3. Click "Copy image"
4. Paste in `image_data` field (remove `data:image/jpeg;base64,` prefix if present)

---

## 🎓 REQUEST 4: START SESSION

**Name**: Start Session
**Method**: POST
**URL**: `{{base_url}}/sessions/start`

**Headers**:
```
Content-Type: application/json
Authorization: Bearer {{token}}
```

**Body** (raw JSON):
```json
{
  "class_id": "CS101",
  "faculty_id": "faculty-001"
}
```

**Tests** (to save session_id):
```javascript
if (pm.response.code === 200) {
    var jsonData = pm.response.json();
    pm.environment.set("session_id", jsonData.id);
    console.log("Session ID saved:", jsonData.id);
}
```

---

## 🚪 REQUEST 5: MARK GATE ENTRY

**Name**: Gate Entry
**Method**: POST
**URL**: `{{base_url}}/attendance/gate-entry`

**Headers**:
```
Content-Type: application/json
Authorization: Bearer {{token}}
```

**Body** (raw JSON):
```json
{
  "student_id": "99220041944",
  "timestamp": "2025-11-22T09:15:00Z"
}
```

**Note**: Only for day scholars!

---

## 🏫 REQUEST 6: MARK CLASSROOM ATTENDANCE

**Name**: Classroom Attendance
**Method**: POST
**URL**: `{{base_url}}/attendance/classroom`

**Headers**:
```
Content-Type: application/json
Authorization: Bearer {{token}}
```

**Body** (raw JSON):
```json
{
  "session_id": "{{session_id}}",
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

## 📊 REQUEST 7: GET ATTENDANCE RECORDS

**Name**: Get Attendance Records
**Method**: GET
**URL**: `{{base_url}}/attendance/session/{{session_id}}/records`

**Headers**:
```
Authorization: Bearer {{token}}
```

---

## 🛑 REQUEST 8: END SESSION

**Name**: End Session
**Method**: POST
**URL**: `{{base_url}}/sessions/{{session_id}}/end`

**Headers**:
```
Authorization: Bearer {{token}}
```

---

## 📋 REQUEST 9: LIST ALL STUDENTS

**Name**: List Students
**Method**: GET
**URL**: `{{base_url}}/students/?class_id=CS101`

**Headers**:
```
Authorization: Bearer {{token}}
```

---

## 🔄 TYPICAL WORKFLOW

### Registering Students (One-time setup):

1. **Login** → Get token
2. **Register Student** → Add student info
3. **Register Face** → Upload student photo
4. Repeat steps 2-3 for each student

### Taking Attendance (Daily):

1. **Login** → Get fresh token
2. **Start Session** → Begin attendance for class
3. **Gate Entry** → Mark day scholars entering gate
4. **Classroom Attendance** → Mark all students in classroom
5. **Get Attendance Records** → View who's present
6. **End Session** → Finalize attendance

---

## 💾 SAVE YOUR COLLECTION

1. Click on your collection
2. Click "..." (three dots)
3. Click "Export"
4. Save as JSON file
5. Share with team members!

---

## 🎯 QUICK TEST SEQUENCE

**Test the entire flow in 2 minutes:**

1. **Login** → Should return token
2. **Register Student** → Use ID: 99220041951
3. **Start Session** → Class: CS101
4. **Gate Entry** → Student: 99220041951
5. **Classroom Attendance** → Student: 99220041951
6. **Get Records** → Should show student present
7. **End Session** → Finalize

---

## 🐛 COMMON ERRORS & FIXES

### Error: "401 Unauthorized"
**Fix**: Run the Login request again to get a fresh token

### Error: "Student already exists"
**Fix**: Change the student_id to a unique value

### Error: "Session not found"
**Fix**: Run "Start Session" first, then use the returned session_id

### Error: "Invalid token"
**Fix**: Token expired. Run Login again.

---

## 📱 MOBILE TESTING

You can also use Postman mobile app:
1. Download Postman app
2. Import your collection
3. Test APIs on the go!

---

## 🔗 USEFUL LINKS

- **API Documentation**: http://localhost:8000/docs
- **Dashboard**: http://localhost:3000
- **Health Check**: http://localhost:8000/api/v1/health

---

## 💡 PRO TIPS

1. **Use Tests tab** to auto-save tokens and IDs
2. **Use Pre-request Scripts** to generate timestamps
3. **Create folders** in collection to organize requests
4. **Use variables** for student IDs to quickly test different students
5. **Save responses** as examples for documentation

---

**Example Pre-request Script for Timestamp:**
```javascript
pm.environment.set("current_timestamp", new Date().toISOString());
```

Then use `{{current_timestamp}}` in your request body!

---

**Last Updated**: November 22, 2025

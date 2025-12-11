# QUICK REFERENCE CARD

## 🎯 SMART ATTENDANCE SYSTEM - CHEAT SHEET

---

## 🔗 IMPORTANT URLS

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:3000 |
| **API Docs** | http://localhost:8000/docs |
| **API Base** | http://localhost:8000/api/v1 |
| **Health** | http://localhost:8000/api/v1/health |

---

## 👥 YOUR STUDENTS (Mock Data)

| Name | ID | Type |
|------|----|----|
| Ashok Reddy | 99220041944 | Day Scholar |
| Revanth | 99220041945 | Hostel |
| Jagadesh | 99220041946 | Day Scholar |
| Yeshwanth | 99220041947 | Hostel |
| Gangadhar | 99220041948 | Day Scholar |
| Yuva | 99220041949 | Day Scholar |
| Kalyan | 99220041950 | Hostel |

---

## 🚀 QUICK START

### 1. Register a Student (Postman)

```http
POST http://localhost:8000/api/v1/students/
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "student_id": "99220041951",
  "name": "Student Name",
  "student_type": "day_scholar",
  "email": "email@example.com",
  "class_id": "CS101"
}
```

### 2. Take Attendance (Dashboard)

1. Go to http://localhost:3000
2. Enter Class ID: **CS101**
3. Click **Start Session**
4. View students in real-time
5. Click **End Session** when done

---

## 📋 API ENDPOINTS

### Authentication
```
POST /api/v1/auth/login
Body: {"username": "admin", "password": "admin123"}
```

### Students
```
POST   /api/v1/students/              # Register student
GET    /api/v1/students/              # List students
GET    /api/v1/students/{id}          # Get student
POST   /api/v1/students/{id}/register-face  # Register face
POST   /api/v1/students/bulk          # Bulk register
```

### Sessions
```
POST   /api/v1/sessions/start         # Start session
POST   /api/v1/sessions/{id}/end      # End session
GET    /api/v1/sessions/{id}          # Get session
```

### Attendance
```
POST   /api/v1/attendance/gate-entry  # Mark gate entry
POST   /api/v1/attendance/classroom   # Mark classroom
GET    /api/v1/attendance/session/{id}/records  # Get records
```

---

## 🔑 AUTHENTICATION

**Get Token:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

**Use Token:**
```
Authorization: Bearer YOUR_TOKEN_HERE
```

---

## 📊 STUDENT TYPES

| Type | Gate Entry | Classroom Entry |
|------|------------|-----------------|
| **day_scholar** | ✅ Required | ✅ Required |
| **hostel_student** | ❌ Not needed | ✅ Required |

---

## 🎓 ATTENDANCE WORKFLOW

```
1. Login → Get Token
2. Start Session → Get Session ID
3. Mark Gate Entry (day scholars only)
4. Mark Classroom Attendance (all students)
5. View Dashboard → See real-time updates
6. End Session → Finalize attendance
```

---

## 🐛 TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| 401 Unauthorized | Get new token (login again) |
| Session auto-restarts | Fixed! Refresh browser |
| Can't register student | Check token, verify student_id is unique |
| Camera not working | Use API for now, camera needs development |
| Students not showing | Check class_id matches, refresh dashboard |

---

## 📁 DOCUMENTATION FILES

| File | Purpose |
|------|---------|
| `HOW_TO_USE_SYSTEM.md` | Complete usage guide |
| `POSTMAN_COLLECTION_GUIDE.md` | Postman setup |
| `STUDENT_DATA.md` | Your student info |
| `QUICK_START_GUIDE.md` | System overview |
| `QUICK_REFERENCE.md` | This file! |

---

## 💡 TIPS

✅ Always get fresh token before API calls
✅ Use same class_id for all students in a class
✅ End sessions properly to save data
✅ Check API docs for more endpoints
✅ Refresh dashboard to see updates

---

## 🆘 HELP

**Check Logs:**
```bash
docker logs api_gateway
docker logs frontend
docker ps  # See all containers
```

**Restart Services:**
```bash
docker-compose -f docker-compose.core.yml restart
```

**Access API Docs:**
http://localhost:8000/docs

---

## 📞 SYSTEM STATUS

**Check if running:**
```bash
docker ps
```

**Should see:**
- smart_attendance_frontend (healthy)
- api_gateway (running)
- smart_attendance_db (healthy)
- smart_attendance_redis (healthy)
- + other services

---

**Last Updated**: November 22, 2025
**Print this for quick reference!**

# STUDENT DATA - SMART ATTENDANCE SYSTEM

## 📋 Mock Student Data (Updated)

The system now includes 7 students with your specified names and ID format.

---

## 👥 STUDENT LIST

| # | Name | Student ID | Type | Status |
|---|------|------------|------|--------|
| 1 | **Ashok Reddy** | 99220041944 | Day Scholar | ✅ Present |
| 2 | **Revanth** | 99220041945 | Hostel Student | ✅ Present |
| 3 | **Jagadesh** | 99220041946 | Day Scholar | ✅ Present |
| 4 | **Yeshwanth** | 99220041947 | Hostel Student | ✅ Present |
| 5 | **Gangadhar** | 99220041948 | Day Scholar | ✅ Present |
| 6 | **Yuva** | 99220041949 | Day Scholar | ❌ Absent |
| 7 | **Kalyan** | 99220041950 | Hostel Student | ✅ Present |

---

## 📊 STATISTICS

- **Total Students**: 7
- **Present**: 6 (86%)
- **Absent**: 1 (14%)
- **Day Scholars**: 4 (3 present, 1 absent)
- **Hostel Students**: 3 (all present)

---

## 🔢 ID FORMAT

**Common Prefix**: `9922004`
**Unique Suffix**: Starting from `1944`

Example:
- First student: `9922004` + `1944` = `99220041944`
- Second student: `9922004` + `1945` = `99220041945`
- And so on...

---

## 📝 DETAILED STUDENT INFORMATION

### 1. Ashok Reddy (99220041944)
- **Type**: Day Scholar
- **Status**: Present
- **Gate Entry**: 09:15 AM
- **Classroom Entry**: 09:30 AM
- **Verification**: ✅ Both gate and classroom verified

### 2. Revanth (99220041945)
- **Type**: Hostel Student
- **Status**: Present
- **Classroom Entry**: 09:28 AM
- **Verification**: ✅ Classroom verified (no gate entry required)

### 3. Jagadesh (99220041946)
- **Type**: Day Scholar
- **Status**: Present
- **Gate Entry**: 09:10 AM
- **Classroom Entry**: 09:31 AM
- **Verification**: ✅ Both gate and classroom verified

### 4. Yeshwanth (99220041947)
- **Type**: Hostel Student
- **Status**: Present
- **Classroom Entry**: 09:32 AM
- **Verification**: ✅ Classroom verified (no gate entry required)

### 5. Gangadhar (99220041948)
- **Type**: Day Scholar
- **Status**: Present
- **Gate Entry**: 09:20 AM
- **Classroom Entry**: 09:35 AM
- **Verification**: ✅ Both gate and classroom verified

### 6. Yuva (99220041949)
- **Type**: Day Scholar
- **Status**: Absent
- **Gate Entry**: 09:12 AM
- **Classroom Entry**: None
- **Verification**: ⚠️ Gate entry only, missing classroom entry

### 7. Kalyan (99220041950)
- **Type**: Hostel Student
- **Status**: Present
- **Classroom Entry**: 09:25 AM
- **Verification**: ✅ Classroom verified (no gate entry required)

---

## 🎯 ATTENDANCE PATTERNS

### Day Scholars (4 students)
- **Ashok Reddy**: ✅ Complete verification
- **Jagadesh**: ✅ Complete verification
- **Gangadhar**: ✅ Complete verification
- **Yuva**: ⚠️ Incomplete (gate entry but no classroom entry)

### Hostel Students (3 students)
- **Revanth**: ✅ Present
- **Yeshwanth**: ✅ Present
- **Kalyan**: ✅ Present

---

## 📱 HOW TO VIEW IN DASHBOARD

1. Go to http://localhost:3000
2. The dashboard will show:
   - Total students: 7
   - Present: 6
   - Absent: 1
   - Attendance: 86%

3. Student list will display all 7 students with their:
   - Names
   - Student IDs (99220041944-99220041950)
   - Present/Absent status
   - Entry times

---

## 🔄 TO ADD MORE STUDENTS

If you want to add more students to the mock data:

1. Edit `frontend/src/services/mockData.ts`
2. Add new student objects following this pattern:
```typescript
{
  id: '8',
  name: 'New Student Name',
  studentId: '99220041951', // Increment the last 4 digits
  type: 'day_scholar' or 'hostel_student',
  isPresent: true or false,
  gateEntry: '2024-01-15T09:XX:00Z', // For day scholars
  classroomEntry: '2024-01-15T09:XX:00Z'
}
```
3. Restart frontend: `docker-compose -f docker-compose.core.yml restart frontend`

---

## 📊 TO REGISTER REAL STUDENTS (VIA API)

Use Postman to register these students in the actual database:

```http
POST http://localhost:8000/api/v1/students/
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json

{
  "student_id": "99220041944",
  "name": "Ashok Reddy",
  "student_type": "day_scholar",
  "email": "ashok.reddy@example.com",
  "phone": "+91-XXXXXXXXXX",
  "class_id": "CS101"
}
```

Repeat for all 7 students with their respective IDs and names.

---

**Last Updated**: November 22, 2025
**Total Students**: 7
**Attendance Rate**: 86%

import { AttendanceSession, Student, EmotionStatistics } from '@/types'

// Mock students data
export const mockStudents: Student[] = [
  {
    id: '1',
    name: 'Ashok Reddy',
    studentId: '99220041944',
    type: 'day_scholar',
    isPresent: true,
    gateEntry: '2024-01-15T09:15:00Z',
    classroomEntry: '2024-01-15T09:30:00Z'
  },
  {
    id: '2',
    name: 'Revanth',
    studentId: '99220041945',
    type: 'hostel_student',
    isPresent: true,
    classroomEntry: '2024-01-15T09:28:00Z'
  },
  {
    id: '3',
    name: 'Jagadesh',
    studentId: '99220041946',
    type: 'day_scholar',
    isPresent: true,
    gateEntry: '2024-01-15T09:10:00Z',
    classroomEntry: '2024-01-15T09:31:00Z'
  },
  {
    id: '4',
    name: 'Yeshwanth',
    studentId: '99220041947',
    type: 'hostel_student',
    isPresent: true,
    classroomEntry: '2024-01-15T09:32:00Z'
  },
  {
    id: '5',
    name: 'Gangadhar',
    studentId: '99220041948',
    type: 'day_scholar',
    isPresent: true,
    gateEntry: '2024-01-15T09:20:00Z',
    classroomEntry: '2024-01-15T09:35:00Z'
  },
  {
    id: '6',
    name: 'Yuva',
    studentId: '99220041949',
    type: 'day_scholar',
    isPresent: false,
    gateEntry: '2024-01-15T09:12:00Z'
  },
  {
    id: '7',
    name: 'Kalyan',
    studentId: '99220041950',
    type: 'hostel_student',
    isPresent: true,
    classroomEntry: '2024-01-15T09:25:00Z'
  }
]

// Mock current session
export const mockCurrentSession: AttendanceSession = {
  id: 'session-001',
  classId: 'CS101',
  facultyId: 'faculty-001',
  startTime: '2024-01-15T09:00:00Z',
  totalRegistered: 7,
  totalDetected: 6,
  attendancePercentage: 86,
  status: 'active'
}

// Mock emotion statistics
export const mockEmotionStats: EmotionStatistics = {
  interested: 65,
  bored: 20,
  confused: 15,
  engagementScore: 72,
  timestamp: '2024-01-15T09:35:00Z'
}
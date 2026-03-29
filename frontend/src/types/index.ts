export interface User {
  id: string
  name: string
  email: string
  role: 'faculty' | 'admin'
}

export interface AttendanceSession {
  id: string
  classId: string
  facultyId: string
  startTime: string
  endTime?: string
  totalRegistered: number
  totalDetected: number
  attendancePercentage: number
  status: 'active' | 'completed'
}

export interface Student {
  id: string
  name: string
  studentId: string
  type: 'day_scholar' | 'hostel_student'
  isPresent: boolean
  gateEntry?: string
  classroomEntry?: string
}

export interface EmotionStatistics {
  interested: number
  bored: number
  confused: number
  engagementScore: number
  timestamp: string
}

export interface AttendanceReport {
  sessionId: string
  date: string
  totalStudents: number
  presentCount: number
  absentCount: number
  attendancePercentage: number
  engagementScore: number
  engagementBreakdown: {
    interested: number
    bored: number
    confused: number
    sleepy: number
  }
  students: {
    studentId: string
    name: string
    type: string
    isPresent: boolean
    gateEntry?: string | null
    classroomEntry?: string | null
    confidence?: number
    emotion?: string | null
    detectionCount?: number
  }[]
  submittedAt: string
  submittedBy: string
}

export interface SystemAlert {
  id: string
  type: 'warning' | 'error' | 'info'
  message: string
  timestamp: string
  acknowledged: boolean
}
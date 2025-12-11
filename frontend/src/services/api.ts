import axios from 'axios'
import { AttendanceSession, Student, AttendanceReport } from '@/types'
import { mockCurrentSession, mockStudents } from './mockData'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'
const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA === 'true' // Use real API by default

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

// Request interceptor for auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized access
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Mock delay function
const mockDelay = (ms: number = 500) => new Promise(resolve => setTimeout(resolve, ms))

export const attendanceAPI = {
  // Get current active session
  getCurrentSession: async (): Promise<AttendanceSession | null> => {
    if (USE_MOCK_DATA) {
      await mockDelay()
      return mockCurrentSession
    }
    
    try {
      const response = await api.get('/attendance/current-session')
      return response.data
    } catch (error) {
      console.error('Error fetching current session:', error)
      return null
    }
  },

  // Start new attendance session
  startSession: async (classId: string): Promise<AttendanceSession> => {
    if (USE_MOCK_DATA) {
      await mockDelay(1000)
      return {
        ...mockCurrentSession,
        classId,
        startTime: new Date().toISOString(),
      }
    }
    
    const response = await api.post('/attendance/start-session', { classId })
    return response.data
  },

  // End attendance session
  endSession: async (sessionId: string): Promise<AttendanceSession> => {
    if (USE_MOCK_DATA) {
      await mockDelay(1000)
      return {
        ...mockCurrentSession,
        id: sessionId,
        endTime: new Date().toISOString(),
        status: 'completed'
      }
    }
    
    const response = await api.post(`/attendance/end-session/${sessionId}`)
    return response.data
  },

  // Get session details
  getSession: async (sessionId: string): Promise<AttendanceSession> => {
    if (USE_MOCK_DATA) {
      await mockDelay()
      return { ...mockCurrentSession, id: sessionId }
    }
    
    const response = await api.get(`/attendance/session/${sessionId}`)
    return response.data
  },

  // Get students for current session
  getSessionStudents: async (sessionId: string): Promise<Student[]> => {
    if (USE_MOCK_DATA) {
      await mockDelay()
      // Simulate some students joining/leaving over time
      const now = Date.now()
      const variation = Math.floor(now / 10000) % 3 // Changes every 10 seconds
      
      return mockStudents.map((student, index) => ({
        ...student,
        isPresent: index < 6 + variation ? student.isPresent : false
      }))
    }
    
    const response = await api.get(`/attendance/session/${sessionId}/students`)
    return response.data
  },

  // Get attendance report
  getAttendanceReport: async (sessionId: string): Promise<AttendanceReport> => {
    if (USE_MOCK_DATA) {
      await mockDelay()
      const presentStudents = mockStudents.filter(s => s.isPresent)
      return {
        sessionId,
        className: 'Computer Science 101',
        date: new Date().toISOString().split('T')[0],
        startTime: '09:00',
        endTime: '10:30',
        totalStudents: mockStudents.length,
        presentStudents: presentStudents.length,
        attendancePercentage: Math.round((presentStudents.length / mockStudents.length) * 100),
        emotionStatistics: {
          interested: 65,
          bored: 20,
          confused: 15,
          engagementScore: 72,
          timestamp: new Date().toISOString()
        },
        students: mockStudents
      }
    }
    
    const response = await api.get(`/attendance/report/${sessionId}`)
    return response.data
  },

  // Get attendance reports by date range
  getReportsByDateRange: async (startDate: string, endDate: string): Promise<AttendanceReport[]> => {
    if (USE_MOCK_DATA) {
      await mockDelay()
      
      // Generate reports from localStorage data
      const attendanceRecords = JSON.parse(localStorage.getItem('attendanceRecords') || '[]')
      const students = JSON.parse(localStorage.getItem('students') || '[]')
      
      if (attendanceRecords.length === 0) {
        return []
      }
      
      // Group records by session
      const sessionMap = new Map<string, any[]>()
      
      attendanceRecords.forEach((record: any) => {
        const recordDate = new Date(record.timestamp).toISOString().split('T')[0]
        
        // Filter by date range
        if (recordDate >= startDate && recordDate <= endDate) {
          const sessionId = record.session_id || 'unknown-session'
          if (!sessionMap.has(sessionId)) {
            sessionMap.set(sessionId, [])
          }
          sessionMap.get(sessionId)!.push(record)
        }
      })
      
      // Generate reports for each session
      const reports: AttendanceReport[] = []
      
      sessionMap.forEach((records, sessionId) => {
        const sessionDate = new Date(records[0].timestamp)
        const presentStudentIds = new Set(records.map(r => r.student_id))
        
        // Calculate engagement metrics
        const engagementCounts = {
          interested: records.filter(r => r.emotion === 'happy' || r.emotion === 'surprised').length,
          bored: records.filter(r => r.emotion === 'neutral' || r.emotion === 'disgusted').length,
          confused: records.filter(r => r.emotion === 'angry' || r.emotion === 'fearful').length,
          sleepy: records.filter(r => r.emotion === 'sad').length,
        }
        
        const totalRecords = records.length
        const engagementScore = totalRecords > 0
          ? Math.round(
              (engagementCounts.interested * 100 +
               engagementCounts.bored * 40 +
               engagementCounts.confused * 20 +
               engagementCounts.sleepy * 0) / totalRecords
            )
          : 0
        
        // Build student list
        const reportStudents = students.map((student: any) => {
          const isPresent = presentStudentIds.has(student.student_id)
          const studentRecords = records.filter(r => r.student_id === student.student_id)
          
          return {
            studentId: student.student_id,
            name: student.name,
            type: student.student_type,
            isPresent,
            gateEntry: isPresent ? studentRecords[0]?.timestamp : null,
            classroomEntry: isPresent ? studentRecords[studentRecords.length - 1]?.timestamp : null,
          }
        })
        
        const presentCount = reportStudents.filter(s => s.isPresent).length
        const totalStudents = reportStudents.length
        
        reports.push({
          sessionId,
          date: sessionDate.toISOString(),
          totalStudents,
          presentCount,
          absentCount: totalStudents - presentCount,
          attendancePercentage: totalStudents > 0 ? Math.round((presentCount / totalStudents) * 100) : 0,
          engagementScore,
          engagementBreakdown: {
            interested: Math.round((engagementCounts.interested / totalRecords) * 100) || 0,
            bored: Math.round((engagementCounts.bored / totalRecords) * 100) || 0,
            confused: Math.round((engagementCounts.confused / totalRecords) * 100) || 0,
            sleepy: Math.round((engagementCounts.sleepy / totalRecords) * 100) || 0,
          },
          students: reportStudents,
        })
      })
      
      // Sort by date (newest first)
      return reports.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
    }
    
    const response = await api.get('/attendance/reports', {
      params: { startDate, endDate }
    })
    return response.data
  },
}

export default api
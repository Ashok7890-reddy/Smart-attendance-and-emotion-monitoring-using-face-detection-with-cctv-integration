import axios from 'axios'
import { AttendanceReport } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
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
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ─── Reports API ──────────────────────────────────────────────────────────────
export const reportsAPI = {
  /**
   * Get attendance reports from submitted sessions stored in localStorage.
   */
  getReportsByDateRange: async (startDate: string, endDate: string): Promise<AttendanceReport[]> => {
    const sessions = JSON.parse(localStorage.getItem('submittedSessions') || '[]')

    if (sessions.length === 0) return []

    const filtered = sessions.filter((s: any) => {
      const sessionDate = (s.endTime || s.submittedAt || '').split('T')[0]
      return sessionDate >= startDate && sessionDate <= endDate
    })

    return filtered.map((s: any) => {
      const emo = s.emotionSummary || s.engagementStats || {}
      const present: any[] = s.finalAttendance?.filter((a: any) => a.status === 'present') || []
      const all: any[] = s.finalAttendance || []

      return {
        sessionId: s.sessionId,
        date: s.endTime || s.submittedAt,
        totalStudents: s.totalRegistered || all.length,
        presentCount: s.presentCount || present.length,
        absentCount: s.absentCount || (all.length - present.length),
        attendancePercentage:
          all.length > 0 ? Math.round(((s.presentCount || present.length) / all.length) * 100) : 0,
        engagementScore: Math.round((emo.avgEngagementScore || 0) * 100),
        engagementBreakdown: {
          interested: emo.interested || 0,
          bored: emo.bored || 0,
          confused: emo.confused || 0,
          sleepy: emo.sleepy || 0,
        },
        students: all.map((a: any) => ({
          studentId: a.student_id,
          name: a.name,
          type: a.student_type,
          isPresent: a.status === 'present',
          emotion: a.emotion,
          confidence: a.confidence,
          detectionCount: a.detectionCount,
        })),
        emotionSummary: s.emotionSummary || null,
        classId: s.classId,
        submittedAt: s.submittedAt,
        submittedBy: s.submittedBy,
      } as AttendanceReport
    }).sort((a: AttendanceReport, b: AttendanceReport) =>
      new Date(b.date).getTime() - new Date(a.date).getTime()
    )
  },
}

// ─── DeepFace Emotion API ──────────────────────────────────────────────────────
export const emotionAPI = {
  /**
   * Analyze a single image for emotion using backend DeepFace service.
   */
  analyzeEmotion: async (
    imageBase64: string,
    studentId = 'unknown'
  ): Promise<{
    emotion: string
    confidence: number
    engagement: string
    engagementScore: number
    rawEmotion: string
    emotionBreakdown: Record<string, number>
  } | null> => {
    try {
      const response = await api.post('/v1/deepface/analyze-emotion-base64', {
        image_base64: imageBase64,
        student_id: studentId,
      })
      const d = response.data
      return {
        emotion: d.raw_emotion,
        confidence: d.confidence,
        engagement: d.emotion,
        engagementScore: d.engagement_score,
        rawEmotion: d.raw_emotion,
        emotionBreakdown: d.emotion_breakdown?.raw_emotions || {},
      }
    } catch {
      return null
    }
  },
}

export default api
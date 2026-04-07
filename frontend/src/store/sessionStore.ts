/**
 * Global Session Store - persists across page navigation.
 * Manages attendance session lifecycle and emotion tracking.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface EmotionSample {
  studentId: string
  emotion: string        // raw: happy, sad, neutral, angry, surprised, disgusted, fearful
  engagement: string     // mapped: interested, bored, confused, sleepy
  engagementScore: number
  timestamp: string
}

export interface AttendeeRecord {
  studentId: string
  name: string
  studentType: string
  detectionCount: number
  firstSeen: string
  lastSeen: string
  emotions: string[]
  avgConfidence: number
}

export interface EmotionSummary {
  interested: number   // percentage
  bored: number
  confused: number
  sleepy: number
  dominant: string
  avgEngagementScore: number
  totalSamples: number
}

export interface SessionSummary {
  sessionId: string
  classId: string
  startTime: string
  endTime: string
  totalRegistered: number
  presentCount: number
  absentCount: number
  attendees: AttendeeRecord[]
  emotionSummary: EmotionSummary
  submittedAt: string
  submittedBy: string
}

interface SessionState {
  // Session info
  sessionId: string | null
  classId: string | null
  startTime: string | null
  isActive: boolean

  // Tracked data during session
  attendees: Record<string, AttendeeRecord>
  emotionSamples: EmotionSample[]
  unrecognizedIntruders: { timestamp: string; imageBase64: string; confidence: number }[]

  // Actions
  startSession: (classId: string) => string
  endSession: () => SessionSummary | null
  recordCapture: (result: CaptureResult, intruders?: { imageBase64: string; confidence: number }[]) => void
  clearSession: () => void

  // Computed
  getAttendeeCount: () => number
  getAverageEmotion: () => EmotionSummary
}

export interface CaptureResult {
  recognizedStudents: Array<{
    studentId: string
    name: string
    studentType: string
    confidence: number
    emotion: string
    engagement: string
    engagementScore: number
  }>
}

const computeEmotionSummary = (samples: EmotionSample[]): EmotionSummary => {
  if (samples.length === 0) {
    return {
      interested: 0, bored: 0, confused: 0, sleepy: 0,
      dominant: 'bored', avgEngagementScore: 0, totalSamples: 0
    }
  }

  const counts = { interested: 0, bored: 0, confused: 0, sleepy: 0 }
  let totalScore = 0

  for (const s of samples) {
    const key = s.engagement as keyof typeof counts
    if (key in counts) counts[key]++
    totalScore += s.engagementScore
  }

  const total = samples.length
  const percentages = {
    interested: Math.round((counts.interested / total) * 100),
    bored: Math.round((counts.bored / total) * 100),
    confused: Math.round((counts.confused / total) * 100),
    sleepy: Math.round((counts.sleepy / total) * 100),
  }

  const dominant = Object.entries(counts).sort(([, a], [, b]) => b - a)[0][0]

  return {
    ...percentages,
    dominant,
    avgEngagementScore: Math.round((totalScore / total) * 100) / 100,
    totalSamples: total,
  }
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      sessionId: null,
      classId: null,
      startTime: null,
      isActive: false,
      attendees: {},
      emotionSamples: [],
      unrecognizedIntruders: [],

      startSession: (classId: string) => {
        const sessionId = `session-${Date.now()}`
        const startTime = new Date().toISOString()
        set({
          sessionId,
          classId,
          startTime,
          isActive: true,
          attendees: {},
          emotionSamples: [],
          unrecognizedIntruders: [],
        })
        console.log(`📚 Session started: ${sessionId} | Class: ${classId}`)
        return sessionId
      },

      endSession: () => {
        const state = get()
        if (!state.isActive || !state.sessionId) return null

        const endTime = new Date().toISOString()
        const allStudents = JSON.parse(localStorage.getItem('students') || '[]')
        const attendeeIds = new Set(Object.keys(state.attendees))

        const absentStudents = allStudents.filter((s: any) => !attendeeIds.has(s.student_id))

        // Build summary
        const summary: SessionSummary = {
          sessionId: state.sessionId,
          classId: state.classId || '',
          startTime: state.startTime || endTime,
          endTime,
          totalRegistered: allStudents.length,
          presentCount: attendeeIds.size,
          absentCount: absentStudents.length,
          attendees: Object.values(state.attendees),
          emotionSummary: computeEmotionSummary(state.emotionSamples),
          submittedAt: endTime,
          submittedBy: 'faculty',
        }

        // Save to submitted sessions
        const submitted = JSON.parse(localStorage.getItem('submittedSessions') || '[]')

        // Build finalAttendance for reports compatibility
        const finalAttendance = [
          ...Object.values(state.attendees).map((a) => ({
            student_id: a.studentId,
            name: a.name,
            student_type: a.studentType,
            status: 'present',
            confidence: a.avgConfidence,
            emotion: a.emotions[a.emotions.length - 1] || 'neutral',
            detectionCount: a.detectionCount,
          })),
          ...absentStudents.map((s: any) => ({
            student_id: s.student_id,
            name: s.name,
            student_type: s.student_type,
            status: 'absent',
            confidence: 0,
            emotion: null,
            detectionCount: 0,
          })),
        ]

        const engStats = summary.emotionSummary
        submitted.push({
          ...summary,
          finalAttendance,
          totalStudents: allStudents.length,
          presentStudents: Array.from(attendeeIds),
          absentStudents: absentStudents.map((s: any) => s.student_id),
          engagementStats: {
            interested: engStats.interested,
            bored: engStats.bored,
            confused: engStats.confused,
            sleepy: engStats.sleepy,
          },
          emotionSamples: state.emotionSamples, // Capture timestamps of emotions
        })
        localStorage.setItem('submittedSessions', JSON.stringify(submitted))

        // Save intruders to local history (limit 100 system-wide)
        if (state.unrecognizedIntruders.length > 0) {
          const globalIntruders = JSON.parse(localStorage.getItem('unrecognizedIntruders') || '[]')
          const updated = [...globalIntruders, ...state.unrecognizedIntruders.map(i => ({ ...i, classId: state.classId, sessionId: state.sessionId }))]
          localStorage.setItem('unrecognizedIntruders', JSON.stringify(updated.slice(-100))) 
        }

        // Also save attendance history
        const history = JSON.parse(localStorage.getItem('attendanceHistory') || '[]')
        finalAttendance.forEach((r) => {
          history.push({ ...r, session_id: state.sessionId, date: endTime.split('T')[0], submitted_at: endTime })
        })
        localStorage.setItem('attendanceHistory', JSON.stringify(history))

        // Clear active session
        set({ isActive: false, sessionId: null, classId: null, startTime: null, attendees: {}, emotionSamples: [] })
        localStorage.removeItem('currentSession')

        console.log(`✅ Session ended. Present: ${summary.presentCount}/${summary.totalRegistered}`)
        console.log(`🎭 Average emotion: ${summary.emotionSummary.dominant} (${summary.emotionSummary.avgEngagementScore} score)`)

        return summary
      },

      recordCapture: (result: CaptureResult, intruders?: { imageBase64: string; confidence: number }[]) => {
        const state = get()
        if (!state.isActive) return

        const now = new Date().toISOString()
        const newAttendees = { ...state.attendees }
        const newSamples = [...state.emotionSamples]
        
        let newIntruders = [...(state.unrecognizedIntruders || [])];
        if (intruders && intruders.length > 0) {
           const toAdd = intruders.map(i => ({ ...i, timestamp: now }));
           newIntruders = [...newIntruders, ...toAdd].slice(-30);
        }

        for (const student of result.recognizedStudents) {
          const { studentId, name, studentType, confidence, emotion, engagement, engagementScore } = student

          // Update attendee record
          if (newAttendees[studentId]) {
            const existing = newAttendees[studentId]
            newAttendees[studentId] = {
              ...existing,
              detectionCount: existing.detectionCount + 1,
              lastSeen: now,
              emotions: [...existing.emotions, emotion],
              avgConfidence: (existing.avgConfidence * existing.detectionCount + confidence) / (existing.detectionCount + 1),
            }
          } else {
            newAttendees[studentId] = {
              studentId, name, studentType,
              detectionCount: 1,
              firstSeen: now,
              lastSeen: now,
              emotions: [emotion],
              avgConfidence: confidence,
            }
          }

          // Track emotion sample
          newSamples.push({ studentId, emotion, engagement, engagementScore, timestamp: now })
        }

        set({ attendees: newAttendees, emotionSamples: newSamples, unrecognizedIntruders: newIntruders })

        // Update localStorage for dashboard display
        localStorage.setItem('currentSession', JSON.stringify({
          id: state.sessionId,
          classId: state.classId,
          startTime: state.startTime,
          presentCount: Object.keys(newAttendees).length,
          sampleCount: newSamples.length,
        }))

        // Also update attendanceRecords for dashboard compatibility
        const records = JSON.parse(localStorage.getItem('attendanceRecords') || '[]')
        for (const student of result.recognizedStudents) {
          if (!records.some((r: any) => r.student_id === student.studentId && r.session_id === state.sessionId)) {
            records.push({
              session_id: state.sessionId,
              student_id: student.studentId,
              name: student.name,
              timestamp: now,
              confidence: student.confidence,
              emotion: student.emotion,
            })
          }
        }
        localStorage.setItem('attendanceRecords', JSON.stringify(records))
      },

      clearSession: () => {
        set({ sessionId: null, classId: null, startTime: null, isActive: false, attendees: {}, emotionSamples: [] })
        localStorage.removeItem('currentSession')
        localStorage.removeItem('attendanceRecords')
      },

      getAttendeeCount: () => Object.keys(get().attendees).length,

      getAverageEmotion: () => computeEmotionSummary(get().emotionSamples),
    }),
    {
      name: 'session-store',
      partialize: (state) => ({
        sessionId: state.sessionId,
        classId: state.classId,
        startTime: state.startTime,
        isActive: state.isActive,
        attendees: state.attendees,
        emotionSamples: state.emotionSamples,
      }),
    }
  )
)

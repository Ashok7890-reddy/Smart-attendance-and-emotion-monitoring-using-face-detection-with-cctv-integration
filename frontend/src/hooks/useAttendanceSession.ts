/**
 * useAttendanceSession — thin wrapper around sessionStore.
 * Keeps backward compatibility with Dashboard components.
 */
import { useMemo } from 'react'
import { useSessionStore } from '@/store/sessionStore'
import { AttendanceSession, Student } from '@/types'

export const useAttendanceSession = () => {
  const store = useSessionStore()

  // Convert attendees map → Student[]
  const students: Student[] = useMemo(() => {
    const allStudents: any[] = JSON.parse(localStorage.getItem('students') || '[]')
    const attendeeKeys = new Set(Object.keys(store.attendees))

    return allStudents.map((s: any) => ({
      id: s.id || s.student_id,
      name: s.name,
      studentId: s.student_id,
      classId: s.class_id || s.classId,
      type: (s.student_type || s.type || 'day_scholar') as 'day_scholar' | 'hostel_student',
      isPresent: attendeeKeys.has(s.student_id),
      emotion: store.attendees[s.student_id]?.emotions?.slice(-1)[0] || undefined,
      confidence: store.attendees[s.student_id]?.avgConfidence || 0,
    }))
  }, [store.attendees])

  const presentStudents = students.filter((s) => s.isPresent)
  const absentStudents = students.filter((s) => !s.isPresent)

  const attendancePercentage =
    students.length > 0 ? Math.round((presentStudents.length / students.length) * 100) : 0

  // Build a compatible AttendanceSession shape for legacy components
  const currentSession: AttendanceSession | null = store.isActive
    ? {
        id: store.sessionId!,
        classId: store.classId!,
        startTime: store.startTime!,
        attendancePercentage,
        presentStudents: presentStudents.length,
        absentStudents: absentStudents.length,
        totalStudents: students.length,
        status: 'active',
      }
    : null

  const startSession = (classId: string) => {
    store.startSession(classId)
  }

  const endSession = (_sessionId: string) => {
    return store.endSession()
  }

  return {
    currentSession,
    students,
    isLoading: false,
    startSession,
    endSession,
    isStarting: false,
    isEnding: false,
    presentStudents,
    absentStudents,
    attendancePercentage,
    emotionSummary: store.getAverageEmotion(),
  }
}
import { useState, useEffect } from 'react'
import { AttendanceSession, Student } from '@/types'

// MOCK MODE: Use localStorage instead of API
export const useAttendanceSession = () => {
  const [currentSession, setCurrentSession] = useState<AttendanceSession | null>(null)
  const [students, setStudents] = useState<Student[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const [isEnding, setIsEnding] = useState(false)

  // Load students from localStorage on mount
  useEffect(() => {
    loadStudents()
    // Refresh every 5 seconds
    const interval = setInterval(loadStudents, 5000)
    return () => clearInterval(interval)
  }, [])

  const loadStudents = () => {
    try {
      const storedStudents = JSON.parse(localStorage.getItem('students') || '[]')
      const attendanceRecords = JSON.parse(localStorage.getItem('attendanceRecords') || '[]')
      
      // Map students with attendance status
      const studentsWithAttendance: Student[] = storedStudents.map((student: any) => {
        const hasAttendance = attendanceRecords.some((record: any) => 
          record.student_id === student.student_id
        )
        
        return {
          id: student.student_id,
          studentId: student.student_id,
          name: student.name,
          type: student.student_type,
          classId: student.class_id,
          email: student.email,
          phone: student.phone,
          isPresent: hasAttendance,
          gateEntry: hasAttendance,
          classroomEntry: hasAttendance,
          emotion: 'interested',
          confidence: 0.95
        }
      })
      
      setStudents(studentsWithAttendance)
    } catch (error) {
      console.error('Error loading students:', error)
    }
  }

  const startSession = async (classId: string) => {
    setIsStarting(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 500))
      const session: AttendanceSession = {
        id: `session-${Date.now()}`,
        classId,
        startTime: new Date().toISOString(),
        endTime: null,
        totalStudents: students.length,
        presentStudents: 0,
        absentStudents: students.length,
        attendancePercentage: 0
      }
      setCurrentSession(session)
      localStorage.setItem('currentSession', JSON.stringify(session))
    } finally {
      setIsStarting(false)
    }
  }

  const endSession = async (sessionId: string) => {
    setIsEnding(true)
    try {
      await new Promise(resolve => setTimeout(resolve, 500))
      setCurrentSession(null)
      localStorage.removeItem('currentSession')
    } finally {
      setIsEnding(false)
    }
  }

  const presentStudents = students.filter(s => s.isPresent)
  const absentStudents = students.filter(s => !s.isPresent)
  const attendancePercentage = students.length > 0 
    ? Math.round((presentStudents.length / students.length) * 100) 
    : 0

  return {
    currentSession,
    students,
    isLoading,
    startSession,
    endSession,
    isStarting,
    isEnding,
    presentStudents,
    absentStudents,
    attendancePercentage,
  }
}
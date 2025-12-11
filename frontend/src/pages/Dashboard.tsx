import React, { useEffect } from 'react'
import { useAttendanceSession } from '@/hooks/useAttendanceSession'
import { AttendanceStats } from '@/components/Dashboard/AttendanceStats'
import { StudentList } from '@/components/Dashboard/StudentList'
import { SessionControls } from '@/components/Dashboard/SessionControls'
import { MissingStudentAlert } from '@/components/Dashboard/MissingStudentAlert'
import { websocketService } from '@/services/websocket'

export const Dashboard: React.FC = () => {
  const {
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
  } = useAttendanceSession()

  // Connect to WebSocket on component mount
  useEffect(() => {
    websocketService.connect()
    
    return () => {
      websocketService.disconnect()
    }
  }, [])

  const missingStudents = absentStudents.filter(student => 
    student.type === 'day_scholar' ? !student.gateEntry || !student.classroomEntry : !student.classroomEntry
  )

  return (
    <div className="space-y-6">
      {/* Session Controls */}
      <SessionControls
        currentSession={currentSession}
        onStartSession={startSession}
        onEndSession={endSession}
        isStarting={isStarting}
        isEnding={isEnding}
      />

      {/* Missing Students Alert */}
      {missingStudents.length > 0 && (
        <MissingStudentAlert missingStudents={missingStudents} />
      )}

      {/* Attendance Statistics */}
      <AttendanceStats
        totalStudents={students.length}
        presentStudents={presentStudents.length}
        absentStudents={absentStudents.length}
        attendancePercentage={attendancePercentage}
        isLive={!!currentSession}
      />

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Student List */}
        <div className="lg:col-span-1">
          <StudentList students={students} isLoading={isLoading} />
        </div>

        {/* Emotion Analytics */}
        <div className="lg:col-span-1">
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Real-time Emotion Analytics
            </h3>
            {currentSession ? (
              <div className="space-y-4">
                <div className="h-48 bg-gray-50 rounded-lg flex items-center justify-center">
                  <div className="text-center text-gray-500">
                    <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-3">
                      <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
                    </div>
                    <p className="text-sm font-medium">Analyzing emotions...</p>
                    <p className="text-xs mt-1">Live emotion data will appear here</p>
                  </div>
                </div>
                <div className="text-center">
                  <button
                    onClick={() => window.location.href = '/analytics'}
                    className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                  >
                    View detailed analytics →
                  </button>
                </div>
              </div>
            ) : (
              <div className="h-48 bg-gray-50 rounded-lg flex items-center justify-center">
                <div className="text-center text-gray-500">
                  <p className="text-sm">Start a session to view emotion analytics</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
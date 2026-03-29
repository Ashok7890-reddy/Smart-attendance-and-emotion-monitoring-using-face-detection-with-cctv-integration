import React, { useEffect, useState } from 'react'
import { useAttendanceSession } from '@/hooks/useAttendanceSession'
import { AttendanceStats } from '@/components/Dashboard/AttendanceStats'
import { StudentList } from '@/components/Dashboard/StudentList'
import { SessionControls } from '@/components/Dashboard/SessionControls'
import { MissingStudentAlert } from '@/components/Dashboard/MissingStudentAlert'
import { websocketService } from '@/services/websocket'

// Recent Submissions Component
const RecentSubmissions: React.FC = () => {
  const [recentSessions, setRecentSessions] = useState<any[]>([])

  useEffect(() => {
    const loadRecentSessions = () => {
      try {
        const submittedSessions = JSON.parse(localStorage.getItem('submittedSessions') || '[]')
        // Get last 3 sessions, sorted by submission time
        const recent = submittedSessions
          .sort((a: any, b: any) => new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime())
          .slice(0, 3)
        setRecentSessions(recent)
      } catch (error) {
        console.error('Error loading recent sessions:', error)
      }
    }

    loadRecentSessions()
    // Refresh every 30 seconds
    const interval = setInterval(loadRecentSessions, 30000)
    return () => clearInterval(interval)
  }, [])

  if (recentSessions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p className="text-sm">No submitted sessions yet</p>
        <p className="text-xs mt-1">Complete a classroom session to see submissions here</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {recentSessions.map((session, index) => (
        <div key={session.sessionId} className="p-3 bg-gray-50 rounded-lg">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-900">
                Session {session.sessionId.split('-')[1]?.slice(-4) || 'Unknown'}
              </p>
              <p className="text-xs text-gray-600">
                {session.presentStudents.length}/{session.totalStudents} present 
                ({Math.round((session.presentStudents.length / session.totalStudents) * 100)}%)
              </p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500">
                {new Date(session.submittedAt).toLocaleDateString()}
              </p>
              <p className="text-xs text-gray-500">
                {new Date(session.submittedAt).toLocaleTimeString()}
              </p>
            </div>
          </div>
          
          {/* Engagement indicator */}
          <div className="mt-2 flex items-center space-x-2">
            <div className="flex-1 bg-gray-200 rounded-full h-1.5">
              <div 
                className="bg-green-500 h-1.5 rounded-full" 
                style={{
                  width: `${Math.round(
                    (session.engagementStats.interested / 
                     (session.engagementStats.interested + session.engagementStats.bored + 
                      session.engagementStats.confused + session.engagementStats.sleepy)) * 100
                  )}%`
                }}
              ></div>
            </div>
            <span className="text-xs text-gray-500">
              {Math.round(
                (session.engagementStats.interested / 
                 (session.engagementStats.interested + session.engagementStats.bored + 
                  session.engagementStats.confused + session.engagementStats.sleepy)) * 100
              )}% engaged
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

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
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Student List */}
        <div className="lg:col-span-2">
          <StudentList students={students} isLoading={isLoading} />
        </div>

        {/* Right Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          {/* Recent Submitted Sessions */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                Recent Submissions
              </h3>
              <button
                onClick={() => window.location.href = '/reports'}
                className="text-primary-600 hover:text-primary-700 text-sm font-medium"
              >
                View All →
              </button>
            </div>
            <RecentSubmissions />
          </div>

          {/* Emotion Analytics */}
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
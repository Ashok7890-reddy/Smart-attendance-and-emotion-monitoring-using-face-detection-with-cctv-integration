import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAttendanceSession } from '@/hooks/useAttendanceSession'
import { AttendanceStats } from '@/components/Dashboard/AttendanceStats'
import { StudentList } from '@/components/Dashboard/StudentList'
import { SessionControls } from '@/components/Dashboard/SessionControls'
import { MissingStudentAlert } from '@/components/Dashboard/MissingStudentAlert'

// ─── Recent Submissions ────────────────────────────────────────────────────────
const RecentSubmissions: React.FC = () => {
  const [recentSessions, setRecentSessions] = useState<any[]>([])

  useEffect(() => {
    const load = () => {
      try {
        const sessions = JSON.parse(localStorage.getItem('submittedSessions') || '[]')
        setRecentSessions(
          sessions
            .sort((a: any, b: any) => new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime())
            .slice(0, 3)
        )
      } catch { /* ignore */ }
    }
    load()
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
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
      {recentSessions.map((session) => {
        const present = session.presentCount ?? (session.presentStudents?.length ?? 0)
        const total = session.totalRegistered ?? session.totalStudents ?? 0
        const pct = total > 0 ? Math.round((present / total) * 100) : 0
        const emo = session.emotionSummary || session.engagementStats || {}
        const intPct = emo.interested ?? 0

        return (
          <div key={session.sessionId} className="p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900">
                  Class: {session.classId || 'Unknown'}
                </p>
                <p className="text-xs text-gray-600">
                  {present}/{total} present ({pct}%) · 
                  <span className="ml-1 capitalize">{emo.dominant || 'N/A'} mood</span>
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

            {/* Engagement bar */}
            <div className="mt-2 flex items-center space-x-2">
              <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                <div
                  className="bg-green-500 h-1.5 rounded-full transition-all"
                  style={{ width: `${intPct}%` }}
                />
              </div>
              <span className="text-xs text-gray-500">{intPct}% engaged</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ─── Past Emotion Analytics ───────────────────────────────────────────────────
const PastEmotionAnalyticsWidget: React.FC<{ isActive: boolean }> = ({ isActive }) => {
  const [latestSession, setLatestSession] = useState<any>(null)

  useEffect(() => {
    const load = () => {
      const sessions = JSON.parse(localStorage.getItem('submittedSessions') || '[]')
      if (sessions.length > 0) {
        // Get the latest session
        const latest = sessions.sort((a: any, b: any) => new Date(b.submittedAt).getTime() - new Date(a.submittedAt).getTime())[0]
        setLatestSession(latest)
      } else {
        setLatestSession(null)
      }
    }
    load()
    // Poll to show newly submitted sessions immediately
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [])

  if (isActive) {
    return (
      <div className="h-48 bg-gray-50 border border-dashed border-gray-200 rounded-xl flex flex-col items-center justify-center p-4 text-center">
        <span className="text-2xl mb-2">🔴</span>
        <p className="text-sm font-semibold text-gray-700">Analytics are being recorded in the background.</p>
        <p className="text-xs text-gray-500 mt-1">Please end the session to view the full emotion analytics report.</p>
      </div>
    )
  }

  if (!latestSession) {
    return (
      <div className="h-48 bg-gray-50 rounded-lg flex items-center justify-center">
        <p className="text-sm text-gray-500">No session submitted yet.</p>
      </div>
    )
  }

  // Extract emotion summary
  const emoSummary = latestSession.emotionSummary || latestSession.engagementStats || {}
  const samples = latestSession.emotionSamples || []

  // Build a timeline if we have samples
  // Group by minute
  let timeline: { time: string, dominant: string, score: number }[] = []
  
  if (samples.length > 0) {
    const grouped: Record<string, any[]> = {}
    samples.forEach((s: any) => {
      // Group by Minute "HH:MM"
      const t = new Date(s.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      if (!grouped[t]) grouped[t] = []
      grouped[t].push(s)
    })

    timeline = Object.keys(grouped).map(time => {
      const minuteSamples = grouped[time]
      let scoreSum = 0
      const counts: Record<string, number> = { interested: 0, bored: 0, confused: 0, sleepy: 0 }
      
      minuteSamples.forEach((s: any) => {
        scoreSum += s.engagementScore || 0
        if (s.engagement in counts) counts[s.engagement]++
      })
      
      const dominant = Object.entries(counts).sort(([,a], [,b]) => b - a)[0][0]
      const avgScore = scoreSum / minuteSamples.length
      
      return { time, dominant, score: avgScore }
    }).sort((a,b) => a.time.localeCompare(b.time))
  }

  const bars = [
    { key: 'interested', label: 'Interested 😊', color: 'bg-green-500', value: emoSummary.interested ?? 0 },
    { key: 'bored',      label: 'Bored 😑',      color: 'bg-yellow-400', value: emoSummary.bored ?? 0 },
    { key: 'confused',   label: 'Confused 😕',   color: 'bg-orange-400', value: emoSummary.confused ?? 0 },
    { key: 'sleepy',     label: 'Sleepy 😴',     color: 'bg-red-400',    value: emoSummary.sleepy ?? 0 },
  ]

  const emojiMap: Record<string, string> = {
    interested: '😊',
    bored: '😑',
    confused: '😕',
    sleepy: '😴',
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-gray-100">
        <span className="text-xs text-gray-500">Report for Class {latestSession.classId || 'Unknown'}</span>
        <span className="text-xs font-semibold text-primary-600 bg-primary-50 px-2 py-0.5 rounded-full">
          Avg Score: {Math.round((emoSummary.avgEngagementScore ?? 0) * 100)}%
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-3 border-r border-gray-100 pr-4">
          <p className="text-xs font-medium text-gray-700">Average Emotion</p>
          {bars.map(({ key, label, color, value }) => (
            <div key={key}>
              <div className="flex justify-between text-[10px] text-gray-600 mb-1">
                <span>{label}</span>
                <span>{value}%</span>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-1.5">
                <div
                  className={`${color} h-1.5 rounded-full`}
                  style={{ width: `${value}%` }}
                />
              </div>
            </div>
          ))}
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-700">Timeline Highlights</p>
          {timeline.length > 0 ? (
            <div className="max-h-28 overflow-y-auto space-y-1.5 pr-2">
              {timeline.map((item, idx) => (
                <div key={idx} className="flex justify-between items-center bg-gray-50 rounded px-2 py-1">
                  <span className="text-[10px] font-mono text-gray-500">{item.time}</span>
                  <div className="flex items-center gap-1.5 align-middle">
                    <span className="text-xs">{emojiMap[item.dominant] || '😐'}</span>
                    <span className="text-[10px] font-semibold text-gray-700 w-8 text-right">
                      {Math.round(item.score * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[10px] text-gray-400 bg-gray-50 rounded p-2 text-center">
              No detailed timeline Data.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
export const Dashboard: React.FC = () => {
  const navigate = useNavigate()
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

  const [sessionSummary, setSessionSummary] = useState<any | null>(null)

  const missingStudents = absentStudents.filter((student) =>
    student.type === 'day_scholar'
      ? !student.gateEntry || !student.classroomEntry
      : !student.classroomEntry
  )

  const handleEndSession = (sessionId: string) => {
    const summary = endSession(sessionId)
    if (summary) setSessionSummary(summary)
  }

  return (
    <div className="space-y-6">
      {/* Session Controls */}
      <SessionControls
        currentSession={currentSession}
        onStartSession={startSession}
        onEndSession={handleEndSession}
        isStarting={isStarting}
        isEnding={isEnding}
      />

      {/* Session ended summary modal */}
      {sessionSummary && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold text-gray-900 mb-1">Session Complete ✅</h2>
            <p className="text-gray-500 text-sm mb-4">Class: {sessionSummary.classId}</p>

            <div className="grid grid-cols-3 gap-3 mb-4">
              {[
                { label: 'Total', value: sessionSummary.totalRegistered, color: 'text-gray-900' },
                { label: 'Present', value: sessionSummary.presentCount, color: 'text-green-600' },
                { label: 'Absent', value: sessionSummary.absentCount, color: 'text-red-500' },
              ].map(({ label, value, color }) => (
                <div key={label} className="text-center bg-gray-50 rounded-lg p-3">
                  <p className={`text-2xl font-bold ${color}`}>{value}</p>
                  <p className="text-xs text-gray-500">{label}</p>
                </div>
              ))}
            </div>

            <div className="bg-blue-50 rounded-xl p-4 mb-4">
              <p className="text-sm font-semibold text-blue-800 mb-2">Average Emotion Analysis</p>
              {Object.entries({
                'Interested 😊': sessionSummary.emotionSummary?.interested ?? 0,
                'Bored 😑': sessionSummary.emotionSummary?.bored ?? 0,
                'Confused 😕': sessionSummary.emotionSummary?.confused ?? 0,
                'Sleepy 😴': sessionSummary.emotionSummary?.sleepy ?? 0,
              }).map(([label, pct]) => (
                <div key={label} className="flex items-center gap-2 mb-1">
                  <span className="text-xs w-24 text-gray-700">{label}</span>
                  <div className="flex-1 bg-blue-100 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full"
                      style={{ width: `${Number(pct)}%` }}
                    />
                  </div>
                  <span className="text-xs text-blue-700 w-8 text-right">{Number(pct)}%</span>
                </div>
              ))}
              <p className="text-xs text-blue-600 mt-2 font-medium">
                Dominant mood:{' '}
                <span className="capitalize">{sessionSummary.emotionSummary?.dominant || 'N/A'}</span>
                {'  ·  '}Engagement: {Math.round((sessionSummary.emotionSummary?.avgEngagementScore ?? 0) * 100)}%
              </p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => { setSessionSummary(null); navigate('/reports') }}
                className="flex-1 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                View Reports
              </button>
              <button
                onClick={() => setSessionSummary(null)}
                className="flex-1 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Missing Students Alert */}
      {missingStudents.length > 0 && (
        <MissingStudentAlert missingStudents={missingStudents} />
      )}

      {/* Attendance Stats */}
      <AttendanceStats
        totalStudents={students.length}
        presentStudents={presentStudents.length}
        absentStudents={absentStudents.length}
        attendancePercentage={attendancePercentage}
        isLive={!!currentSession}
      />

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <StudentList students={students} isLoading={isLoading} />
        </div>

        <div className="lg:col-span-1 space-y-6">
          {/* Recent Submissions */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Recent Submissions</h3>
              <button
                onClick={() => navigate('/reports')}
                className="text-primary-600 hover:text-primary-700 text-sm font-medium"
              >
                View All →
              </button>
            </div>
            <RecentSubmissions />
          </div>

          {/* Emotion Analytics Report */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Emotion Analytics Report
            </h3>
            <PastEmotionAnalyticsWidget isActive={!!currentSession} />
            {currentSession && (
              <div className="mt-3 text-center">
                <button
                  onClick={() => navigate('/classroom-camera')}
                  className="text-primary-600 hover:text-primary-700 text-sm font-medium"
                >
                  Open Classroom Camera →
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
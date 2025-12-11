import React from 'react'
import { useAttendanceSession } from '@/hooks/useAttendanceSession'
import { EmotionDashboard } from '@/components/Analytics/EmotionDashboard'

export const Analytics: React.FC = () => {
  const { currentSession } = useAttendanceSession()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Emotion Analytics Dashboard
            </h2>
            <p className="text-gray-600 mt-1">
              Real-time student engagement and emotion analysis
            </p>
          </div>
          {currentSession && (
            <div className="flex items-center space-x-2 text-sm">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
              <span className="text-green-600 font-medium">Session Active</span>
              <span className="text-gray-500">({currentSession.classId})</span>
            </div>
          )}
        </div>
      </div>

      {/* Emotion Analytics */}
      <EmotionDashboard sessionId={currentSession?.id} />
    </div>
  )
}
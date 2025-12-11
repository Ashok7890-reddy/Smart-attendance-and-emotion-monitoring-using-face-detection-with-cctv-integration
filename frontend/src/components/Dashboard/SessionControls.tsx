import React, { useState } from 'react'
import { 
  PlayIcon, 
  StopIcon, 
  ClockIcon,
  ExclamationTriangleIcon 
} from '@heroicons/react/24/outline'
import { AttendanceSession } from '@/types'
import { format } from 'date-fns'

interface SessionControlsProps {
  currentSession: AttendanceSession | null
  onStartSession: (classId: string) => void
  onEndSession: (sessionId: string) => void
  isStarting: boolean
  isEnding: boolean
}

export const SessionControls: React.FC<SessionControlsProps> = ({
  currentSession,
  onStartSession,
  onEndSession,
  isStarting,
  isEnding
}) => {
  const [showEndConfirm, setShowEndConfirm] = useState(false)
  const [classId, setClassId] = useState('CS101') // Default class ID

  const handleStartSession = () => {
    onStartSession(classId)
  }

  const handleEndSession = () => {
    if (currentSession) {
      onEndSession(currentSession.id)
      setShowEndConfirm(false)
    }
  }

  if (currentSession) {
    return (
      <div className="card bg-green-50 border-green-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Session Active
              </h3>
              <div className="flex items-center space-x-4 text-sm text-gray-600">
                <span className="flex items-center">
                  <ClockIcon className="h-4 w-4 mr-1" />
                  Started: {format(new Date(currentSession.startTime), 'HH:mm')}
                </span>
                <span>Class: {currentSession.classId}</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {!showEndConfirm ? (
              <button
                onClick={() => setShowEndConfirm(true)}
                className="flex items-center px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors duration-200"
                disabled={isEnding}
              >
                <StopIcon className="h-5 w-5 mr-2" />
                End Session
              </button>
            ) : (
              <div className="flex items-center space-x-2">
                <div className="flex items-center text-sm text-red-600 mr-3">
                  <ExclamationTriangleIcon className="h-5 w-5 mr-1" />
                  End session?
                </div>
                <button
                  onClick={() => setShowEndConfirm(false)}
                  className="px-3 py-1 text-sm bg-gray-200 hover:bg-gray-300 text-gray-700 rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={handleEndSession}
                  disabled={isEnding}
                  className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded disabled:opacity-50"
                >
                  {isEnding ? 'Ending...' : 'Confirm'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            Start Attendance Session
          </h3>
          <p className="text-sm text-gray-600">
            Begin tracking attendance for your class
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          <div>
            <label htmlFor="classId" className="block text-sm font-medium text-gray-700 mb-1">
              Class ID
            </label>
            <input
              type="text"
              id="classId"
              value={classId}
              onChange={(e) => setClassId(e.target.value)}
              className="input-field w-32"
              placeholder="CS101"
            />
          </div>
          
          <button
            onClick={handleStartSession}
            disabled={isStarting || !classId.trim()}
            className="flex items-center px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PlayIcon className="h-5 w-5 mr-2" />
            {isStarting ? 'Starting...' : 'Start Session'}
          </button>
        </div>
      </div>
    </div>
  )
}
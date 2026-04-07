import React, { useState, useEffect } from 'react'
import { EyeIcon, CpuChipIcon, ClockIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { checkBackendHealth } from '@/services/faceService'
import { useSessionStore } from '@/store/sessionStore'

export const SystemStatus: React.FC = () => {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)
  const sampleCount = useSessionStore((s) => s.emotionSamples.length)
  const attendeeCount = useSessionStore((s) => Object.keys(s.attendees).length)
  const isActive = useSessionStore((s) => s.isActive)
  const students = JSON.parse(localStorage.getItem('students') || '[]')

  useEffect(() => {
    const check = () => checkBackendHealth().then(setBackendOnline)
    check()
    const id = setInterval(check, 15000)
    return () => clearInterval(id)
  }, [])

  const statusRows = [
    {
      label: 'Face Recognition Engine',
      value: backendOnline ? 'DeepFace (Facenet512)' : 'Local Fallback',
      status: backendOnline ? 'High' : 'Medium',
      icon: <CheckCircleIcon className="h-5 w-5" />,
    },
    {
      label: 'Face Detector',
      value: backendOnline ? 'RetinaFace' : 'Descriptor Match',
      status: backendOnline ? 'High' : 'Standard',
      icon: <EyeIcon className="h-5 w-5" />,
    },
    {
      label: 'Emotion Analysis',
      value: backendOnline ? 'DeepFace Analyze' : 'Unavailable (need backend)',
      status: backendOnline ? 'High' : 'Standard',
      icon: <CpuChipIcon className="h-5 w-5" />,
    },
  ]

  const getStatusColor = (status: string) => ({
    High:     'text-green-700 bg-green-100',
    Medium:   'text-yellow-700 bg-yellow-100',
    Standard: 'text-blue-700 bg-blue-100',
  }[status] || 'text-gray-600 bg-gray-100')

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-sm font-semibold text-gray-900">System Status</h3>
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          backendOnline === true ? 'bg-green-100 text-green-700' :
          backendOnline === false ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-500'
        }`}>
          {backendOnline === true ? '🟢 Backend Online' : backendOnline === false ? '🟡 Backend Offline' : '⚪ Checking…'}
        </span>
      </div>

      {/* Live stats */}
      <div className="grid grid-cols-3 gap-2 mb-5">
        {[
          { label: 'Registered', value: students.length, icon: '👤' },
          { label: isActive ? 'Present' : 'Sessions', value: isActive ? attendeeCount : JSON.parse(localStorage.getItem('submittedSessions') || '[]').length, icon: isActive ? '✅' : '📋' },
          { label: 'Samples', value: sampleCount, icon: '🎭' },
        ].map(({ label, value, icon }) => (
          <div key={label} className="bg-gray-50 rounded-lg p-2.5 text-center">
            <p className="text-base font-bold text-gray-900">{icon} {value}</p>
            <p className="text-xs text-gray-500">{label}</p>
          </div>
        ))}
      </div>

      {/* Engine status */}
      <div className="space-y-2">
        {statusRows.map(({ label, value, status, icon }) => (
          <div key={label} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`${status === 'High' ? 'text-green-500' : status === 'Medium' ? 'text-yellow-500' : 'text-gray-400'}`}>
                {icon}
              </span>
              <div>
                <p className="text-xs font-medium text-gray-700">{label}</p>
                <p className="text-xs text-gray-400">{value}</p>
              </div>
            </div>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getStatusColor(status)}`}>
              {status}
            </span>
          </div>
        ))}
      </div>

      {/* Backend start tip */}
      {backendOnline === false && (
        <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-lg text-xs text-orange-700">
          <p className="font-semibold mb-1">Start backend for full DeepFace accuracy:</p>
          <code className="bg-orange-100 px-1.5 py-0.5 rounded font-mono block mt-1">
            python start_backend.py
          </code>
        </div>
      )}
    </div>
  )
}
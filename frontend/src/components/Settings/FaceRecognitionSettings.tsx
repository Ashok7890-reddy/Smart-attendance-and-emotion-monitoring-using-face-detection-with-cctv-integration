import React, { useState, useEffect } from 'react'
import { CogIcon, EyeIcon, ChartBarIcon, BeakerIcon } from '@heroicons/react/24/outline'
import { checkBackendHealth } from '@/services/faceService'

export const FaceRecognitionSettings: React.FC = () => {
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null)
  const [captureInterval, setCaptureInterval] = useState(
    Number(localStorage.getItem('captureInterval') || '5')
  )
  const [confidenceThreshold, setConfidenceThreshold] = useState(
    Number(localStorage.getItem('confidenceThreshold') || '70')
  )

  useEffect(() => {
    const check = () => checkBackendHealth().then(setBackendOnline)
    check()
    const id = setInterval(check, 10000)
    return () => clearInterval(id)
  }, [])

  const saveSettings = () => {
    localStorage.setItem('captureInterval', String(captureInterval))
    localStorage.setItem('confidenceThreshold', String(confidenceThreshold))
    setTestResult({ ok: true, message: 'Settings saved successfully!' })
    setTimeout(() => setTestResult(null), 3000)
  }

  const runBackendTest = async () => {
    setLoading(true)
    setTestResult(null)
    const ok = await checkBackendHealth()
    setBackendOnline(ok)
    if (ok) {
      setTestResult({ ok: true, message: '✅ Backend is online! DeepFace (Facenet512 + RetinaFace) is ready.' })
    } else {
      setTestResult({ ok: false, message: '⚠ Backend offline. Start it with: python start_backend.py' })
    }
    setLoading(false)
  }

  const clearAllData = () => {
    if (window.confirm('Clear all attendance records and sessions? Students will NOT be deleted.')) {
      localStorage.removeItem('submittedSessions')
      localStorage.removeItem('attendanceRecords')
      localStorage.removeItem('attendanceHistory')
      localStorage.removeItem('gateEntries')
      localStorage.removeItem('currentSession')
      setTestResult({ ok: true, message: 'Attendance data cleared.' })
      setTimeout(() => setTestResult(null), 3000)
    }
  }

  return (
    <div className="space-y-6">
      {/* Engine Info */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-3 mb-5">
          <CogIcon className="h-6 w-6 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">Face Recognition Configuration</h2>
        </div>

        {/* Backend status */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          {[
            {
              label: 'Face Detector',
              value: backendOnline ? 'RetinaFace' : 'N/A (backend offline)',
              icon: <EyeIcon className="h-5 w-5 text-gray-400" />,
              color: backendOnline ? 'text-green-700' : 'text-orange-600',
            },
            {
              label: 'Recognition Model',
              value: backendOnline ? 'Facenet512 (512D)' : 'Local descriptors',
              icon: <ChartBarIcon className="h-5 w-5 text-gray-400" />,
              color: backendOnline ? 'text-green-700' : 'text-yellow-600',
            },
            {
              label: 'Emotion Engine',
              value: backendOnline ? 'DeepFace Analyze' : 'Offline',
              icon: <BeakerIcon className="h-5 w-5 text-gray-400" />,
              color: backendOnline ? 'text-green-700' : 'text-red-500',
            },
          ].map(({ label, value, icon, color }) => (
            <div key={label} className="bg-gray-50 rounded-xl p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-gray-500">{label}</span>
                {icon}
              </div>
              <p className={`text-sm font-semibold ${color}`}>{value}</p>
            </div>
          ))}
        </div>

        {/* Backend start instructions */}
        <div className={`rounded-xl p-4 border ${backendOnline ? 'bg-green-50 border-green-200' : 'bg-orange-50 border-orange-200'}`}>
          <p className={`text-sm font-semibold mb-1 ${backendOnline ? 'text-green-800' : 'text-orange-800'}`}>
            {backendOnline ? '🟢 Backend Running' : '🟡 Backend Offline'}
          </p>
          {!backendOnline && (
            <>
              <p className="text-xs text-orange-700 mb-2">Start the backend for full DeepFace accuracy:</p>
              <div className="space-y-1 text-xs font-mono bg-orange-100 rounded-lg p-3 text-orange-900">
                <p># Install (first time only)</p>
                <p>pip install -r requirements_backend.txt</p>
                <p className="mt-1"># Run</p>
                <p>python start_backend.py</p>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Capture Settings */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h3 className="text-base font-semibold text-gray-900 mb-4">Capture Settings</h3>
        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Capture Interval: <span className="text-primary-600 font-semibold">{captureInterval}s</span>
            </label>
            <input
              type="range"
              min={3}
              max={30}
              step={1}
              value={captureInterval}
              onChange={(e) => setCaptureInterval(Number(e.target.value))}
              className="w-full accent-primary-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>3s (frequent)</span>
              <span>30s (battery-friendly)</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Confidence Threshold: <span className="text-primary-600 font-semibold">{confidenceThreshold}%</span>
            </label>
            <input
              type="range"
              min={50}
              max={95}
              step={5}
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
              className="w-full accent-primary-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>50% (lenient)</span>
              <span>95% (strict)</span>
            </div>
          </div>

          <button
            onClick={saveSettings}
            className="px-5 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            Save Settings
          </button>
        </div>
      </div>

      {/* System Test */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-base font-semibold text-gray-900">System Test</h3>
          <button
            onClick={runBackendTest}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {loading ? 'Testing…' : 'Test Backend Connection'}
          </button>
        </div>

        {testResult && (
          <div className={`p-3 rounded-lg border text-sm ${testResult.ok ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
            {testResult.message}
          </div>
        )}

        <div className="mt-4 pt-4 border-t border-gray-100">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Data Management</h4>
          <button
            onClick={clearAllData}
            className="px-4 py-2 bg-red-50 hover:bg-red-100 border border-red-200 text-red-700 rounded-lg text-sm font-medium transition-colors"
          >
            🗑 Clear Attendance Records
          </button>
          <p className="text-xs text-gray-400 mt-1">Clears sessions and records. Student registrations are preserved.</p>
        </div>
      </div>
    </div>
  )
}
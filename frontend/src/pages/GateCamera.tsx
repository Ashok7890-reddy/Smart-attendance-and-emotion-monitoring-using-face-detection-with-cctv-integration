import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AutoCaptureCamera } from '@/components/Camera/AutoCaptureCamera'
import { ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline'
import { analyzeFrame, captureFrameBase64 } from '@/services/faceService'

interface GateEntry {
  student_id: string
  name: string
  timestamp: string
  confidence: number
  status: 'success' | 'error'
  emotion?: string
}

export const GateCamera: React.FC = () => {
  const navigate = useNavigate()
  const [entries, setEntries] = useState<GateEntry[]>([])
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handlePhotoCapture = async (imageData: string) => {
    setProcessing(true)
    setError(null)

    try {
      // Strip data-URL prefix if present
      const b64 = imageData.includes(',') ? imageData.split(',')[1] : imageData

      const result = await analyzeFrame(b64, `gate-${Date.now()}`)

      if (result.recognizedStudents.length === 0) {
        throw new Error(
          result.totalFaces > 0
            ? 'Face detected but not recognized. Please register first.'
            : 'No face detected. Please look at the camera.'
        )
      }

      const student = result.recognizedStudents[0]

      // Record gate entry
      const gateEntries = JSON.parse(localStorage.getItem('gateEntries') || '[]')
      gateEntries.push({
        student_id: student.studentId,
        name: student.name,
        student_type: student.studentType,
        timestamp: new Date().toISOString(),
        confidence: student.confidence,
        emotion: student.emotion,
      })
      localStorage.setItem('gateEntries', JSON.stringify(gateEntries))

      setEntries((prev) => [{
        student_id: student.studentId,
        name: student.name,
        timestamp: new Date().toLocaleTimeString(),
        confidence: student.confidence,
        status: 'success',
        emotion: student.emotion,
      }, ...prev])

    } catch (err: any) {
      setError(err.message)
      setEntries((prev) => [{
        student_id: 'Unknown',
        name: 'Not Recognized',
        timestamp: new Date().toLocaleTimeString(),
        confidence: 0,
        status: 'error',
      }, ...prev])
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between bg-white rounded-xl border border-gray-200 px-5 py-3 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse" />
          <span className="text-sm font-semibold text-green-700">Gate Camera Active</span>
        </div>
        <button onClick={() => navigate('/')} className="text-sm text-primary-600 hover:text-primary-700 font-medium">
          ← Dashboard
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Camera */}
        <div className="lg:col-span-2 space-y-3">
          <AutoCaptureCamera
            title="Gate Entry Camera — Auto Capture"
            subtitle="Camera automatically captures and recognizes day scholars every 3 seconds"
            onCapture={handlePhotoCapture}
            captureInterval={3000}
          />

          {processing && (
            <div className="flex items-center gap-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600" />
              <span className="text-sm text-blue-700">Processing face recognition via DeepFace…</span>
            </div>
          )}

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              ⚠ {error}
            </div>
          )}
        </div>

        {/* Entry Log */}
        <div className="space-y-3">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <div className="flex items-center gap-2 mb-4">
              <ArrowRightOnRectangleIcon className="h-5 w-5 text-primary-600" />
              <h3 className="text-sm font-semibold text-gray-900">Recent Gate Entries</h3>
            </div>

            <div className="space-y-2 max-h-72 overflow-y-auto">
              {entries.length === 0 ? (
                <p className="text-xs text-gray-400 text-center py-6">No entries yet. Waiting for students…</p>
              ) : (
                entries.map((entry, i) => (
                  <div
                    key={i}
                    className={`p-2.5 rounded-lg border text-xs ${
                      entry.status === 'success'
                        ? 'bg-green-50 border-green-200'
                        : 'bg-red-50 border-red-200'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div>
                        <p className={`font-semibold ${entry.status === 'success' ? 'text-green-800' : 'text-red-800'}`}>
                          {entry.name}
                        </p>
                        <p className={entry.status === 'success' ? 'text-green-600' : 'text-red-500'}>
                          ID: {entry.student_id}
                          {entry.confidence > 0 && ` · ${Math.round(entry.confidence * 100)}%`}
                          {entry.emotion && ` · ${entry.emotion}`}
                        </p>
                      </div>
                      <span className={entry.status === 'success' ? 'text-green-500' : 'text-red-400'}>
                        {entry.timestamp}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>

            {entries.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-600 space-y-0.5">
                <p>Total: <span className="font-semibold">{entries.length}</span></p>
                <p>Recognized: <span className="font-semibold text-green-600">{entries.filter(e => e.status === 'success').length}</span></p>
                <p>Failed: <span className="font-semibold text-red-500">{entries.filter(e => e.status === 'error').length}</span></p>
              </div>
            )}
          </div>

          {/* Info box */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-700 space-y-1">
            <p className="font-semibold text-blue-800 mb-1.5">ℹ️ Gate Entry Info</p>
            <p>• Only for Day Scholars</p>
            <p>• Recognized via DeepFace (Facenet512)</p>
            <p>• Entry time is recorded automatically</p>
            <p>• Students must also mark classroom attendance</p>
          </div>
        </div>
      </div>
    </div>
  )
}

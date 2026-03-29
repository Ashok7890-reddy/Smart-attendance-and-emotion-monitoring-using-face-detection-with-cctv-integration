import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AutoCaptureCamera } from '@/components/Camera/AutoCaptureCamera'
import { ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline'
import { enhancedFaceService } from '@/services/enhancedFaceService'

interface GateEntry {
  student_id: string
  name: string
  timestamp: string
  status: 'success' | 'error'
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
      console.log('🔍 Recognizing face with REAL ML...')
      
      // Create optimized image element for enhanced recognition
      const img = await enhancedFaceService.createImageElement(imageData)

      // Detect face using enhanced service (ONNX + face-api.js hybrid)
      const detection = await enhancedFaceService.detectFace(img)
      
      if (!detection) {
        throw new Error('No face detected in image')
      }

      console.log('✅ Face detected! Confidence:', detection.detection.score.toFixed(3))
      console.log('🎯 Model used:', detection.modelUsed)
      console.log('📊 Embedding dimension:', detection.embeddingDimension + 'D')
      console.log('⚡ Processing time:', detection.processingTime?.toFixed(1) + 'ms')

      // Get registered students
      const students = JSON.parse(localStorage.getItem('students') || '[]')
      
      if (students.length === 0) {
        throw new Error('No students registered. Please register students first.')
      }

      // Find best match using REAL face recognition
      let bestMatch = null
      let bestSimilarity = 0
      // Dynamic threshold based on model used
      const threshold = detection.modelUsed?.includes('ONNX') ? 0.85 : 0.60 // Higher threshold for ONNX models

      console.log(`🔍 Comparing face against ${students.length} registered students...`)

      for (const student of students) {
        const storedDescriptor = new Float32Array(student.face_descriptor)
        const similarity = enhancedFaceService.compareFaces(
          detection.descriptor,
          storedDescriptor
        )

        console.log(`Comparing with ${student.name}: ${(similarity * 100).toFixed(1)}%`)

        if (similarity > bestSimilarity) {
          bestSimilarity = similarity
          if (similarity > threshold) {
            bestMatch = student
            console.log(`✅ New best match: ${student.name} (${(similarity * 100).toFixed(1)}%)`)
          } else {
            console.log(`⚠️ Close but below threshold: ${student.name} (${(similarity * 100).toFixed(1)}% < 60%)`)
          }
        }
      }

      const thresholdPercent = (threshold * 100).toFixed(0)
      console.log(`📊 Best similarity found: ${(bestSimilarity * 100).toFixed(1)}% (threshold: ${thresholdPercent}%)`)
      console.log(`🎯 Recognition model: ${detection.modelUsed} (${detection.embeddingDimension}D embeddings)`)

      if (!bestMatch) {
        throw new Error(`Face not recognized (best match: ${(bestSimilarity * 100).toFixed(1)}%, threshold: ${thresholdPercent}%). Please register first.`)
      }

      console.log(`✅ RECOGNIZED: ${bestMatch.name} with ${(bestSimilarity * 100).toFixed(1)}% confidence`)

      // Record gate entry
      const gateEntries = JSON.parse(localStorage.getItem('gateEntries') || '[]')
      gateEntries.push({
        student_id: bestMatch.student_id,
        name: bestMatch.name,
        timestamp: new Date().toISOString(),
        confidence: bestSimilarity
      })
      localStorage.setItem('gateEntries', JSON.stringify(gateEntries))

      // Add to UI
      const newEntry: GateEntry = {
        student_id: bestMatch.student_id,
        name: bestMatch.name,
        timestamp: new Date().toLocaleTimeString(),
        status: 'success'
      }

      setEntries([newEntry, ...entries])
      
    } catch (err: any) {
      console.error('Recognition error:', err)
      setError(err.message)
      
      const errorEntry: GateEntry = {
        student_id: 'Unknown',
        name: 'Recognition Failed',
        timestamp: new Date().toLocaleTimeString(),
        status: 'error'
      }
      setEntries([errorEntry, ...entries])
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={() => navigate('/')}
            className="text-primary-600 hover:text-primary-700 font-medium"
          >
            ← Back to Dashboard
          </button>
          <div className="flex items-center space-x-2 text-green-600">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <span className="font-medium">Gate Camera Active</span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Camera Section */}
          <div className="lg:col-span-2">
            <AutoCaptureCamera
              title="Gate Entry Camera - Auto Capture"
              subtitle="Camera automatically captures and recognizes students every 3 seconds"
              onCapture={handlePhotoCapture}
              captureInterval={3000}
            />

            {processing && (
              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mr-3"></div>
                  <span className="text-blue-700">Processing face recognition...</span>
                </div>
              </div>
            )}

            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}
          </div>

          {/* Recent Entries Section */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-lg p-6">
              <div className="flex items-center mb-4">
                <ArrowRightOnRectangleIcon className="h-6 w-6 text-primary-600 mr-2" />
                <h3 className="text-lg font-semibold text-gray-900">Recent Gate Entries</h3>
              </div>

              <div className="space-y-3">
                {entries.length === 0 ? (
                  <p className="text-sm text-gray-500 text-center py-8">
                    No entries yet. Waiting for students...
                  </p>
                ) : (
                  entries.map((entry, index) => (
                    <div
                      key={index}
                      className={`p-3 rounded-lg border ${
                        entry.status === 'success'
                          ? 'bg-green-50 border-green-200'
                          : 'bg-red-50 border-red-200'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <p className={`font-medium ${
                            entry.status === 'success' ? 'text-green-900' : 'text-red-900'
                          }`}>
                            {entry.name}
                          </p>
                          <p className={`text-sm ${
                            entry.status === 'success' ? 'text-green-600' : 'text-red-600'
                          }`}>
                            ID: {entry.student_id}
                          </p>
                        </div>
                        <span className={`text-xs ${
                          entry.status === 'success' ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {entry.timestamp}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>

              {entries.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <div className="text-sm text-gray-600">
                    <p>Total Entries: <span className="font-semibold">{entries.length}</span></p>
                    <p>Successful: <span className="font-semibold text-green-600">
                      {entries.filter(e => e.status === 'success').length}
                    </span></p>
                    <p>Failed: <span className="font-semibold text-red-600">
                      {entries.filter(e => e.status === 'error').length}
                    </span></p>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800 font-medium mb-2">ℹ️ Gate Entry Info</p>
              <ul className="text-xs text-blue-700 space-y-1">
                <li>• Only for Day Scholars</li>
                <li>• Face will be recognized automatically</li>
                <li>• Entry time is recorded</li>
                <li>• Must also mark classroom attendance</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

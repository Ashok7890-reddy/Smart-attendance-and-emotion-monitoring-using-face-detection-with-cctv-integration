import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AutoCaptureCamera } from '@/components/Camera/AutoCaptureCamera'
import { EmotionAnalytics } from '@/components/EmotionAnalytics'
import { AcademicCapIcon, UserGroupIcon } from '@heroicons/react/24/outline'
import { faceApiService } from '@/services/faceApiService'

interface AttendanceEntry {
  student_id: string
  name: string
  student_type: string
  timestamp: string
  confidence: number
  status: 'success' | 'error'
  emotion?: string
  emotion_confidence?: number
  engagement?: string
}

export const ClassroomCamera: React.FC = () => {
  const navigate = useNavigate()
  const [entries, setEntries] = useState<AttendanceEntry[]>([])
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionActive, setSessionActive] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)

  const handlePhotoCapture = async (imageData: string) => {
    setProcessing(true)
    setError(null)

    try {
      console.log('🔍 Detecting faces in classroom with REAL ML...')
      
      // Create image element
      const img = await faceApiService.createImageElement(imageData)

      // Detect ALL faces in classroom
      const detections = await faceApiService.detectMultipleFaces(img)
      
      if (detections.length === 0) {
        throw new Error('No faces detected in classroom')
      }

      console.log(`✅ Detected ${detections.length} face(s) in classroom`)

      // Get registered students
      const students = JSON.parse(localStorage.getItem('students') || '[]')
      
      if (students.length === 0) {
        throw new Error('No students registered')
      }

      // Match each detected face
      const recognizedStudents = []
      const threshold = 0.6

      for (let i = 0; i < detections.length; i++) {
        const detection = detections[i]
        let bestMatch = null
        let bestSimilarity = 0

        for (const student of students) {
          const storedDescriptor = new Float32Array(student.face_descriptor)
          const similarity = faceApiService.compareFaces(
            detection.descriptor,
            storedDescriptor
          )

          if (similarity > bestSimilarity && similarity > threshold) {
            bestSimilarity = similarity
            bestMatch = student
          }
        }

        if (bestMatch) {
          // Get emotion using REAL emotion detection
          const emotionResult = faceApiService.getEmotion(detection.expressions)
          
          console.log(`Face ${i + 1}: ${bestMatch.name} (${(bestSimilarity * 100).toFixed(1)}%) - Emotion: ${emotionResult.emotion}`)
          
          recognizedStudents.push({
            ...bestMatch,
            confidence: bestSimilarity,
            emotion: emotionResult.emotion,
            emotion_confidence: emotionResult.confidence
          })
        } else {
          console.log(`Face ${i + 1}: Not recognized (best: ${(bestSimilarity * 100).toFixed(1)}%)`)
        }
      }

      console.log(`✅ Recognized ${recognizedStudents.length} out of ${detections.length} faces`)

      // Record attendance
      const attendanceRecords = JSON.parse(localStorage.getItem('attendanceRecords') || '[]')
      const newRecords = recognizedStudents.map(student => ({
        session_id: sessionId,
        student_id: student.student_id,
        name: student.name,
        timestamp: new Date().toISOString(),
        confidence: student.confidence,
        emotion: student.emotion
      }))
      
      attendanceRecords.push(...newRecords)
      localStorage.setItem('attendanceRecords', JSON.stringify(attendanceRecords))

      // Map emotions to engagement levels for classroom evaluation
      const getEngagement = (emotion: string): string => {
        const engagementMap: { [key: string]: string } = {
          'happy': 'interested',
          'surprised': 'interested',
          'neutral': 'bored',
          'sad': 'sleepy',
          'disgusted': 'bored',
          'angry': 'confused',
          'fearful': 'confused'
        }
        return engagementMap[emotion] || 'bored'
      }

      // Update UI
      const newEntries: AttendanceEntry[] = recognizedStudents.map(student => ({
        student_id: student.student_id,
        name: student.name,
        student_type: student.student_type,
        timestamp: new Date().toLocaleTimeString(),
        confidence: student.confidence,
        status: 'success',
        emotion: student.emotion,
        emotion_confidence: student.emotion_confidence,
        engagement: getEngagement(student.emotion)
      }))

      setEntries([...newEntries, ...entries])
      
    } catch (err: any) {
      console.error('Attendance error:', err)
      setError(err.message)
    } finally {
      setProcessing(false)
    }
  }

  const startSession = () => {
    setSessionActive(true)
    setSessionId(`session-${Date.now()}`)
    setEntries([])
  }

  const endSession = () => {
    setSessionActive(false)
    setSessionId(null)
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
          <div className="flex items-center space-x-4">
            {sessionActive ? (
              <>
                <div className="flex items-center space-x-2 text-green-600">
                  <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="font-medium">Session Active</span>
                </div>
                <button
                  onClick={endSession}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                >
                  End Session
                </button>
              </>
            ) : (
              <button
                onClick={startSession}
                className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
              >
                Start Session
              </button>
            )}
          </div>
        </div>

        {!sessionActive ? (
          <div className="bg-white rounded-lg shadow-lg p-12 text-center">
            <AcademicCapIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">No Active Session</h2>
            <p className="text-gray-600 mb-6">Start a session to begin taking attendance</p>
            <button
              onClick={startSession}
              className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
            >
              Start Attendance Session
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {/* Camera Section */}
            <div className="lg:col-span-2 xl:col-span-2">
              <AutoCaptureCamera
                title="Classroom Attendance Camera - Auto Capture"
                subtitle="Camera automatically captures and marks attendance every 5 seconds"
                onCapture={handlePhotoCapture}
                captureInterval={5000}
              />

              {processing && (
                <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mr-3"></div>
                    <span className="text-blue-700">Detecting faces and marking attendance...</span>
                  </div>
                </div>
              )}

              {error && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}

              <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800 font-medium mb-2">💡 Auto-Capture Mode</p>
                <ul className="text-xs text-yellow-700 space-y-1">
                  <li>• Camera captures automatically every 5 seconds</li>
                  <li>• All registered students are marked present</li>
                  <li>• Click "Start Auto Capture" to begin</li>
                  <li>• Click "Pause" to stop auto-capture</li>
                </ul>
              </div>
            </div>

            {/* Right Sidebar - Attendance & Analytics */}
            <div className="lg:col-span-2 xl:col-span-1 space-y-6">
              {/* Emotion Analytics Dashboard */}
              <EmotionAnalytics entries={entries} />

              {/* Attendance Log Section */}
              <div>
              <div className="bg-white rounded-lg shadow-lg p-6">
                <div className="flex items-center mb-4">
                  <UserGroupIcon className="h-6 w-6 text-primary-600 mr-2" />
                  <h3 className="text-lg font-semibold text-gray-900">Attendance Log</h3>
                </div>

                <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                  <div className="text-sm text-gray-600">
                    <p>Session ID: <span className="font-mono text-xs">{sessionId}</span></p>
                    <p className="mt-1">Students Marked: <span className="font-semibold text-primary-600">
                      {entries.filter(e => e.status === 'success').length}
                    </span></p>
                  </div>
                </div>

                {/* Emotion Analytics */}
                {entries.length > 0 && (
                  <div className="mb-4 p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg border border-purple-200">
                    <h4 className="text-sm font-semibold text-purple-900 mb-3">😊 Class Engagement</h4>
                    {(() => {
                      const interested = entries.filter(e => e.engagement === 'interested').length
                      const bored = entries.filter(e => e.engagement === 'bored').length
                      const confused = entries.filter(e => e.engagement === 'confused').length
                      const sleepy = entries.filter(e => e.engagement === 'sleepy').length
                      const total = entries.length

                      return (
                        <div className="space-y-2">
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-green-700 font-medium">😊 Interested</span>
                              <span className="text-green-700 font-bold">{interested} ({total > 0 ? Math.round(interested/total*100) : 0}%)</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div className="bg-green-500 h-2 rounded-full" style={{width: `${total > 0 ? (interested/total*100) : 0}%`}}></div>
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-yellow-700 font-medium">😐 Bored</span>
                              <span className="text-yellow-700 font-bold">{bored} ({total > 0 ? Math.round(bored/total*100) : 0}%)</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div className="bg-yellow-500 h-2 rounded-full" style={{width: `${total > 0 ? (bored/total*100) : 0}%`}}></div>
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-orange-700 font-medium">😕 Confused</span>
                              <span className="text-orange-700 font-bold">{confused} ({total > 0 ? Math.round(confused/total*100) : 0}%)</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div className="bg-orange-500 h-2 rounded-full" style={{width: `${total > 0 ? (confused/total*100) : 0}%`}}></div>
                            </div>
                          </div>
                          <div>
                            <div className="flex justify-between text-xs mb-1">
                              <span className="text-red-700 font-medium">😴 Sleepy</span>
                              <span className="text-red-700 font-bold">{sleepy} ({total > 0 ? Math.round(sleepy/total*100) : 0}%)</span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div className="bg-red-500 h-2 rounded-full" style={{width: `${total > 0 ? (sleepy/total*100) : 0}%`}}></div>
                            </div>
                          </div>
                        </div>
                      )
                    })()}
                  </div>
                )}

                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {entries.length === 0 ? (
                    <p className="text-sm text-gray-500 text-center py-8">
                      No students detected yet. Capture a photo to begin.
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
                            <div className="flex items-center gap-2">
                              <p className={`font-medium text-sm ${
                                entry.status === 'success' ? 'text-green-900' : 'text-red-900'
                              }`}>
                                {entry.name}
                              </p>
                              {entry.emotion && (
                                <span className="text-lg" title={`${entry.emotion} (${(entry.emotion_confidence! * 100).toFixed(0)}%)`}>
                                  {entry.emotion === 'happy' && '😊'}
                                  {entry.emotion === 'sad' && '😢'}
                                  {entry.emotion === 'angry' && '😠'}
                                  {entry.emotion === 'fearful' && '😨'}
                                  {entry.emotion === 'surprised' && '😲'}
                                  {entry.emotion === 'disgusted' && '🤢'}
                                  {entry.emotion === 'neutral' && '😐'}
                                </span>
                              )}
                            </div>
                            <p className={`text-xs ${
                              entry.status === 'success' ? 'text-green-600' : 'text-red-600'
                            }`}>
                              ID: {entry.student_id}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              {entry.student_type}
                              {entry.status === 'success' && ` • ${(entry.confidence * 100).toFixed(0)}% match`}
                            </p>
                            {entry.emotion && entry.engagement && (
                              <div className="mt-1 flex items-center gap-1">
                                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                                  entry.engagement === 'interested' ? 'bg-green-100 text-green-700' :
                                  entry.engagement === 'bored' ? 'bg-yellow-100 text-yellow-700' :
                                  entry.engagement === 'confused' ? 'bg-orange-100 text-orange-700' :
                                  'bg-red-100 text-red-700'
                                }`}>
                                  {entry.engagement}
                                </span>
                                <span className="text-xs text-gray-500">
                                  {entry.emotion} ({(entry.emotion_confidence! * 100).toFixed(0)}%)
                                </span>
                              </div>
                            )}
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
              </div>

              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800 font-medium mb-2">ℹ️ Classroom Attendance</p>
                <ul className="text-xs text-blue-700 space-y-1">
                  <li>• Required for ALL students</li>
                  <li>• Day scholars need gate entry first</li>
                  <li>• Hostel students: classroom only</li>
                  <li>• Multiple captures allowed</li>
                </ul>
              </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

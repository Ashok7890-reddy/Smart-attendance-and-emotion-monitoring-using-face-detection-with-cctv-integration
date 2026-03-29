import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AutoCaptureCamera } from '@/components/Camera/AutoCaptureCamera'
import { EmotionAnalytics } from '@/components/EmotionAnalytics'
import { AcademicCapIcon, UserGroupIcon } from '@heroicons/react/24/outline'
import { enhancedFaceService } from '@/services/enhancedFaceService'
import { emotionAPI } from '@/services/api'

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
  engagement_score?: number
  emotion_breakdown?: any
}

interface SessionSummary {
  sessionId: string
  startTime: string
  endTime: string
  totalStudents: number
  presentStudents: string[]
  absentStudents: string[]
  engagementStats: {
    interested: number
    bored: number
    confused: number
    sleepy: number
  }
}

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

export const ClassroomCamera: React.FC = () => {
  const navigate = useNavigate()
  const [entries, setEntries] = useState<AttendanceEntry[]>([])
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionActive, setSessionActive] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [sessionStartTime, setSessionStartTime] = useState<string | null>(null)
  const [showSubmissionModal, setShowSubmissionModal] = useState(false)
  const [sessionSummary, setSessionSummary] = useState<SessionSummary | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const handlePhotoCapture = async (imageData: string) => {
    setProcessing(true)
    setError(null)

    try {
      console.log('🔍 Detecting faces in classroom with REAL ML...')
      
      // Create optimized image element for enhanced recognition
      const img = await enhancedFaceService.createImageElement(imageData)

      // Detect ALL faces in classroom using enhanced service (ONNX + face-api.js hybrid)
      const detections = await enhancedFaceService.detectMultipleFaces(img)
      
      if (detections.length === 0) {
        throw new Error('No faces detected in classroom')
      }

      console.log(`✅ Detected ${detections.length} face(s) in classroom`)
      if (detections.length > 0) {
        const modelUsed = detections[0].modelUsed
        const embeddingDim = detections[0].embeddingDimension
        console.log(`🎯 Detection model: ${modelUsed} (${embeddingDim}D embeddings)`)
        console.log(`⚡ Processing time: ${detections[0].processingTime?.toFixed(1)}ms`)
      }

      // Get registered students
      const students = JSON.parse(localStorage.getItem('students') || '[]')
      
      if (students.length === 0) {
        throw new Error('No students registered')
      }

      // Match each detected face
      const recognizedStudents = []
      // Lower threshold for better recognition (was 0.60, now 0.35)
      const threshold = detections.length > 0 && detections[0].modelUsed?.includes('ONNX') ? 0.75 : 0.35

      console.log(`🔍 Comparing ${detections.length} faces against ${students.length} registered students...`)
      console.log(`🎯 Recognition threshold: ${(threshold * 100).toFixed(0)}%`)

      for (let i = 0; i < detections.length; i++) {
        const detection = detections[i]
        let bestMatch = null
        let bestSimilarity = 0
        let allSimilarities: Array<{name: string, similarity: number}> = []

        console.log(`\n--- Face ${i + 1} Analysis ---`)
        console.log(`Face detection confidence: ${(detection.detection.score * 100).toFixed(1)}%`)

        for (const student of students) {
          const storedDescriptor = new Float32Array(student.face_descriptor)
          const similarity = enhancedFaceService.compareFaces(
            detection.descriptor,
            storedDescriptor
          )

          allSimilarities.push({name: student.name, similarity})
          console.log(`Comparing with ${student.name}: ${(similarity * 100).toFixed(1)}%`)

          if (similarity > bestSimilarity) {
            bestSimilarity = similarity
            if (similarity > threshold) {
              bestMatch = student
              console.log(`✅ New best match: ${student.name} (${(similarity * 100).toFixed(1)}%)`)
            } else {
              const thresholdPercent = (threshold * 100).toFixed(0)
              console.log(`⚠️ Close but below threshold: ${student.name} (${(similarity * 100).toFixed(1)}% < ${thresholdPercent}%)`)
            }
          }
        }

        // Show top 3 matches for debugging
        const topMatches = allSimilarities
          .sort((a, b) => b.similarity - a.similarity)
          .slice(0, 3)
        console.log(`📊 Top 3 matches for Face ${i + 1}:`)
        topMatches.forEach((match, idx) => {
          console.log(`  ${idx + 1}. ${match.name}: ${(match.similarity * 100).toFixed(1)}%`)
        })
        
        console.log(`📊 Face ${i + 1} best similarity: ${(bestSimilarity * 100).toFixed(1)}%`)

        if (bestMatch) {
          // Emotion analysis: try DeepFace (backend) first, then face-api.js, then fallback
          let emotionResult

          try {
            // 1st: Try DeepFace via backend API
            const deepfaceResult = await emotionAPI.analyzeEmotion(imageData, bestMatch.student_id)

            if (deepfaceResult) {
              emotionResult = {
                emotion: deepfaceResult.rawEmotion,
                confidence: deepfaceResult.confidence,
                engagement: deepfaceResult.engagement,
                engagementScore: deepfaceResult.engagementScore
              }
              console.log(`🧠 DeepFace emotion: ${deepfaceResult.rawEmotion} → ${deepfaceResult.engagement} (${(deepfaceResult.engagementScore * 100).toFixed(1)}%)`)
            } else {
              // 2nd: Fall back to face-api.js emotion detection
              console.warn('DeepFace unavailable, falling back to face-api.js...')
              const simpleEmotion = await enhancedFaceService.getSimpleEmotion(imageData)
              emotionResult = {
                emotion: simpleEmotion.emotion,
                confidence: simpleEmotion.confidence,
                engagement: simpleEmotion.engagement,
                engagementScore: simpleEmotion.engagementScore
              }
              console.log(`🎭 face-api.js emotion: ${simpleEmotion.emotion} → ${simpleEmotion.engagement}`)
            }
          } catch (error) {
            console.warn('Emotion analysis failed, using expression fallback:', error)
            // 3rd: Last resort — use raw detection expressions
            const fallbackEmotion = enhancedFaceService.getEmotion(detection.expressions)
            emotionResult = {
              emotion: fallbackEmotion.emotion,
              confidence: fallbackEmotion.confidence,
              engagement: getEngagement(fallbackEmotion.emotion),
              engagementScore: 0.5
            }
          }
          
          recognizedStudents.push({
            ...bestMatch,
            confidence: bestSimilarity,
            emotion: emotionResult.emotion,
            emotion_confidence: emotionResult.confidence,
            engagement: emotionResult.engagement,
            engagement_score: emotionResult.engagementScore
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

      // Update UI
      const newEntries: AttendanceEntry[] = recognizedStudents.map(student => {
        const engagement = student.engagement || getEngagement(student.emotion)
        console.log(`🎯 Student: ${student.name}`)
        console.log(`🎭 Emotion: ${student.emotion} → Engagement: ${engagement}`)
        
        return {
          student_id: student.student_id,
          name: student.name,
          student_type: student.student_type,
          timestamp: new Date().toLocaleTimeString(),
          confidence: student.confidence,
          status: 'success',
          emotion: student.emotion,
          emotion_confidence: student.emotion_confidence,
          engagement: engagement,
          engagement_score: student.engagement_score
        }
      })

      console.log(`📊 Adding ${newEntries.length} new entries to analytics`)
      setEntries([...newEntries, ...entries])
      
    } catch (err: any) {
      console.error('Attendance error:', err)
      setError(err.message)
    } finally {
      setProcessing(false)
    }
  }

  const startSession = () => {
    const newSessionId = `session-${Date.now()}`
    const startTime = new Date().toISOString()
    
    setSessionActive(true)
    setSessionId(newSessionId)
    setSessionStartTime(startTime)
    setEntries([])
    setError(null)
    
    console.log(`📚 Started attendance session: ${newSessionId}`)
  }

  const endSession = () => {
    if (!sessionId || !sessionStartTime) return
    
    // Generate session summary
    const endTime = new Date().toISOString()
    const uniqueStudents = [...new Set(entries.filter(e => e.status === 'success').map(e => e.student_id))]
    const allStudents = JSON.parse(localStorage.getItem('students') || '[]')
    const presentStudentIds = uniqueStudents
    const absentStudentIds = allStudents
      .map((s: any) => s.student_id)
      .filter((id: string) => !presentStudentIds.includes(id))
    
    // Calculate engagement statistics
    const engagementStats = {
      interested: entries.filter(e => e.engagement === 'interested').length,
      bored: entries.filter(e => e.engagement === 'bored').length,
      confused: entries.filter(e => e.engagement === 'confused').length,
      sleepy: entries.filter(e => e.engagement === 'sleepy').length
    }
    
    const summary: SessionSummary = {
      sessionId,
      startTime: sessionStartTime,
      endTime,
      totalStudents: allStudents.length,
      presentStudents: presentStudentIds,
      absentStudents: absentStudentIds,
      engagementStats
    }
    
    setSessionSummary(summary)
    setSessionActive(false)
    setShowSubmissionModal(true)
    
    console.log(`📚 Ended attendance session: ${sessionId}`)
    console.log(`👥 Present: ${presentStudentIds.length}/${allStudents.length} students`)
  }

  const submitAttendance = async () => {
    if (!sessionSummary) return
    
    setSubmitting(true)
    
    try {
      // Get existing submitted sessions
      const submittedSessions = JSON.parse(localStorage.getItem('submittedSessions') || '[]')
      
      // Create final attendance submission
      const submission = {
        ...sessionSummary,
        submittedAt: new Date().toISOString(),
        submittedBy: 'faculty', // In real app, get from auth context
        status: 'submitted',
        finalAttendance: sessionSummary.presentStudents.map(studentId => {
          const student = JSON.parse(localStorage.getItem('students') || '[]')
            .find((s: any) => s.student_id === studentId)
          const studentEntries = entries.filter(e => e.student_id === studentId && e.status === 'success')
          const avgConfidence = studentEntries.reduce((sum, e) => sum + e.confidence, 0) / studentEntries.length
          const dominantEmotion = studentEntries.length > 0 ? studentEntries[studentEntries.length - 1].emotion : 'neutral'
          
          return {
            student_id: studentId,
            name: student?.name || 'Unknown',
            student_type: student?.student_type || 'unknown',
            status: 'present',
            confidence: avgConfidence,
            emotion: dominantEmotion,
            detectionCount: studentEntries.length
          }
        })
      }
      
      // Add absent students
      const absentStudents = JSON.parse(localStorage.getItem('students') || '[]')
        .filter((s: any) => sessionSummary.absentStudents.includes(s.student_id))
        .map((student: any) => ({
          student_id: student.student_id,
          name: student.name,
          student_type: student.student_type,
          status: 'absent',
          confidence: 0,
          emotion: null,
          detectionCount: 0
        }))
      
      submission.finalAttendance.push(...absentStudents)
      
      // Save submission
      submittedSessions.push(submission)
      localStorage.setItem('submittedSessions', JSON.stringify(submittedSessions))
      
      // Update student attendance records
      const attendanceHistory = JSON.parse(localStorage.getItem('attendanceHistory') || '[]')
      submission.finalAttendance.forEach(record => {
        attendanceHistory.push({
          ...record,
          session_id: sessionSummary.sessionId,
          date: new Date().toISOString().split('T')[0],
          submitted_at: submission.submittedAt
        })
      })
      localStorage.setItem('attendanceHistory', JSON.stringify(attendanceHistory))
      
      console.log('✅ Attendance submitted successfully!')
      console.log(`📊 Final attendance: ${submission.finalAttendance.filter(s => s.status === 'present').length}/${submission.finalAttendance.length} present`)
      
      // Reset state
      setShowSubmissionModal(false)
      setSessionSummary(null)
      setSessionId(null)
      setSessionStartTime(null)
      setEntries([])
      
      // Show success message
      alert('Attendance submitted successfully!')
      
    } catch (error) {
      console.error('Failed to submit attendance:', error)
      alert('Failed to submit attendance. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const cancelSubmission = () => {
    setShowSubmissionModal(false)
    // Allow faculty to continue the session or start a new one
    setSessionSummary(null)
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
                <div className="text-sm text-gray-600">
                  Students Detected: <span className="font-semibold text-primary-600">
                    {[...new Set(entries.filter(e => e.status === 'success').map(e => e.student_id))].length}
                  </span>
                </div>
                <button
                  onClick={endSession}
                  className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors"
                >
                  End & Review
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

              <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800 font-medium mb-2">📋 Attendance Submission</p>
                <ul className="text-xs text-blue-700 space-y-1">
                  <li>• Click "End & Review" when class is finished</li>
                  <li>• Review attendance summary before submitting</li>
                  <li>• Submitted attendance will be saved permanently</li>
                  <li>• View submitted records in Reports section</li>
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

        {/* Attendance Submission Modal */}
        {showSubmissionModal && sessionSummary && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-6">
                  <h2 className="text-xl font-bold text-gray-900">Submit Attendance</h2>
                  <button
                    onClick={cancelSubmission}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Session Summary */}
                <div className="mb-6 p-4 bg-gray-50 rounded-lg">
                  <h3 className="font-semibold text-gray-900 mb-3">Session Summary</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Session ID:</span>
                      <p className="font-mono text-xs">{sessionSummary.sessionId}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Duration:</span>
                      <p>{new Date(sessionSummary.startTime).toLocaleTimeString()} - {new Date(sessionSummary.endTime).toLocaleTimeString()}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Total Students:</span>
                      <p className="font-semibold">{sessionSummary.totalStudents}</p>
                    </div>
                    <div>
                      <span className="text-gray-600">Present:</span>
                      <p className="font-semibold text-green-600">{sessionSummary.presentStudents.length}</p>
                    </div>
                  </div>
                </div>

                {/* Attendance Overview */}
                <div className="mb-6">
                  <h3 className="font-semibold text-gray-900 mb-3">Attendance Overview</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                      <span className="text-green-800 font-medium">Present Students</span>
                      <span className="text-green-800 font-bold">{sessionSummary.presentStudents.length}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
                      <span className="text-red-800 font-medium">Absent Students</span>
                      <span className="text-red-800 font-bold">{sessionSummary.absentStudents.length}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                      <span className="text-blue-800 font-medium">Attendance Rate</span>
                      <span className="text-blue-800 font-bold">
                        {Math.round((sessionSummary.presentStudents.length / sessionSummary.totalStudents) * 100)}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Engagement Statistics */}
                <div className="mb-6">
                  <h3 className="font-semibold text-gray-900 mb-3">Class Engagement</h3>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-3 bg-green-50 rounded-lg">
                      <div className="text-green-800 font-medium">😊 Interested</div>
                      <div className="text-green-800 font-bold">{sessionSummary.engagementStats.interested}</div>
                    </div>
                    <div className="p-3 bg-yellow-50 rounded-lg">
                      <div className="text-yellow-800 font-medium">😐 Bored</div>
                      <div className="text-yellow-800 font-bold">{sessionSummary.engagementStats.bored}</div>
                    </div>
                    <div className="p-3 bg-orange-50 rounded-lg">
                      <div className="text-orange-800 font-medium">😕 Confused</div>
                      <div className="text-orange-800 font-bold">{sessionSummary.engagementStats.confused}</div>
                    </div>
                    <div className="p-3 bg-red-50 rounded-lg">
                      <div className="text-red-800 font-medium">😴 Sleepy</div>
                      <div className="text-red-800 font-bold">{sessionSummary.engagementStats.sleepy}</div>
                    </div>
                  </div>
                </div>

                {/* Present Students List */}
                {sessionSummary.presentStudents.length > 0 && (
                  <div className="mb-6">
                    <h3 className="font-semibold text-gray-900 mb-3">Present Students ({sessionSummary.presentStudents.length})</h3>
                    <div className="max-h-32 overflow-y-auto bg-gray-50 rounded-lg p-3">
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        {sessionSummary.presentStudents.map(studentId => {
                          const student = JSON.parse(localStorage.getItem('students') || '[]')
                            .find((s: any) => s.student_id === studentId)
                          return (
                            <div key={studentId} className="text-green-700">
                              {student?.name || studentId}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                )}

                {/* Absent Students List */}
                {sessionSummary.absentStudents.length > 0 && (
                  <div className="mb-6">
                    <h3 className="font-semibold text-gray-900 mb-3">Absent Students ({sessionSummary.absentStudents.length})</h3>
                    <div className="max-h-32 overflow-y-auto bg-gray-50 rounded-lg p-3">
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        {sessionSummary.absentStudents.map(studentId => {
                          const student = JSON.parse(localStorage.getItem('students') || '[]')
                            .find((s: any) => s.student_id === studentId)
                          return (
                            <div key={studentId} className="text-red-700">
                              {student?.name || studentId}
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex justify-end space-x-4 pt-4 border-t">
                  <button
                    onClick={cancelSubmission}
                    disabled={submitting}
                    className="px-6 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={submitAttendance}
                    disabled={submitting}
                    className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50 flex items-center"
                  >
                    {submitting ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Submitting...
                      </>
                    ) : (
                      'Submit Attendance'
                    )}
                  </button>
                </div>

                <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-800">
                    <strong>Note:</strong> Once submitted, this attendance record will be finalized and saved to the system. 
                    You can view submitted records in the Reports section.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

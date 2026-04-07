import React, { useRef, useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSessionStore } from '@/store/sessionStore'
import { analyzeFrame, captureFrameBase64, checkBackendHealth, FaceRecognitionResult } from '@/services/faceService'

// ─── Types ────────────────────────────────────────────────────────────────────
interface DetectionLog {
  ts: string
  students: FaceRecognitionResult[]
  facesTotal: number
  unrecognized: number
  backendOnline: boolean
  error?: string
}

// ─── Emotion badge ────────────────────────────────────────────────────────────
const EmotionBadge: React.FC<{ emotion: string }> = ({ emotion }) => {
  const map: Record<string, { bg: string; label: string }> = {
    happy:     { bg: 'bg-green-100 text-green-700',  label: '😊 Happy' },
    surprised: { bg: 'bg-blue-100 text-blue-700',   label: '😲 Surprised' },
    neutral:   { bg: 'bg-gray-100 text-gray-600',   label: '😐 Neutral' },
    sad:       { bg: 'bg-indigo-100 text-indigo-600',label: '😢 Sad' },
    angry:     { bg: 'bg-red-100 text-red-700',     label: '😠 Angry' },
    disgusted: { bg: 'bg-purple-100 text-purple-600',label: '🤢 Disgusted' },
    fearful:   { bg: 'bg-yellow-100 text-yellow-700',label: '😨 Fearful' },
  }
  const style = map[emotion?.toLowerCase()] || map.neutral
  return <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${style.bg}`}>{style.label}</span>
}

// ─── Engagement color ─────────────────────────────────────────────────────────
const engagementColor = (eng: string) => ({
  interested: 'text-green-600',
  bored:      'text-yellow-600',
  confused:   'text-orange-500',
  sleepy:     'text-red-500',
}[eng] || 'text-gray-600')

// ─── Main component ───────────────────────────────────────────────────────────
export const ClassroomCamera: React.FC = () => {
  const navigate = useNavigate()
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const captureTimerRef = useRef<NodeJS.Timeout | null>(null)

  const { isActive, sessionId, classId } = useSessionStore()

  const [cameraOn, setCameraOn] = useState(false)
  const [capturing, setCapturing] = useState(false)
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)
  const [captureInterval, setCaptureInterval] = useState(5) // seconds
  const [logs, setLogs] = useState<DetectionLog[]>([])
  const [lastResult, setLastResult] = useState<DetectionLog | null>(null)
  const [error, setError] = useState<string | null>(null)
  const recordCapture = useSessionStore((s) => s.recordCapture)
  const emotionSummary = useSessionStore((s) => s.getAverageEmotion())
  const sampleCount = useSessionStore((s) => s.emotionSamples.length)
  const attendeeCount = useSessionStore((s) => Object.keys(s.attendees).length)
  const unrecognizedIntruders = useSessionStore((s) => s.unrecognizedIntruders)

  const [showIntruderAlert, setShowIntruderAlert] = useState(false)

  // Check backend on mount
  useEffect(() => {
    checkBackendHealth().then(setBackendOnline)
  }, [])

  // Auto-start camera if session is active
  useEffect(() => {
    if (isActive && !cameraOn) startCamera()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isActive])

  const startCamera = useCallback(async () => {
    try {
      setError(null)
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setCameraOn(true)
    } catch (err: any) {
      setError(`Camera access denied: ${err.message}`)
    }
  }, [])

  const stopCamera = useCallback(() => {
    if (captureTimerRef.current) {
      clearInterval(captureTimerRef.current)
      captureTimerRef.current = null
    }
    setCapturing(false)
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setCameraOn(false)
  }, [])

  // Capture a single frame and analyze
  const captureAndAnalyze = useCallback(async () => {
    if (!videoRef.current || !sessionId) return

    const b64 = captureFrameBase64(videoRef.current, 0.8)
    if (!b64) return

    try {
      const result = await analyzeFrame(b64, sessionId)
      const online = !result.error?.includes('Backend offline')
      setBackendOnline(online)

      const logEntry: DetectionLog = {
        ts: new Date().toLocaleTimeString(),
        students: result.recognizedStudents,
        facesTotal: result.totalFaces,
        unrecognized: result.unrecognizedCount,
        backendOnline: online,
        error: result.error,
      }

      setLastResult(logEntry)
      setLogs((prev) => [logEntry, ...prev].slice(0, 50))

      if (result.recognizedStudents.length > 0 || (result.unrecognizedFaces && result.unrecognizedFaces.length > 0)) {
        recordCapture(
          { recognizedStudents: result.recognizedStudents }, 
          result.unrecognizedFaces
        )
      }

      if (result.unrecognizedCount > 0) {
        setShowIntruderAlert(true)
        setTimeout(() => setShowIntruderAlert(false), 3000)
      }

    } catch (err: any) {
      console.error('[ClassroomCamera] Capture failed:', err.message)
    }
  }, [sessionId, recordCapture])

  const startCapturing = useCallback(() => {
    if (!isActive) {
      setError('No active session. Start a session on the Dashboard first.')
      return
    }
    setCapturing(true)
    captureAndAnalyze() // immediate first capture
    captureTimerRef.current = setInterval(captureAndAnalyze, captureInterval * 1000)
  }, [isActive, captureInterval, captureAndAnalyze])

  const stopCapturing = useCallback(() => {
    if (captureTimerRef.current) {
      clearInterval(captureTimerRef.current)
      captureTimerRef.current = null
    }
    setCapturing(false)
  }, [])

  // Cleanup on unmount
  useEffect(() => () => {
    stopCapturing()
    // Don't stop camera/session on navigate — session persists
  }, [stopCapturing])

  const emotionBars = [
    { key: 'interested', label: '😊 Interested', color: 'bg-green-500', value: emotionSummary.interested },
    { key: 'bored',      label: '😑 Bored',      color: 'bg-yellow-400', value: emotionSummary.bored },
    { key: 'confused',   label: '😕 Confused',   color: 'bg-orange-400', value: emotionSummary.confused },
    { key: 'sleepy',     label: '😴 Sleepy',     color: 'bg-red-400',    value: emotionSummary.sleepy },
  ]

  return (
    <div className="space-y-4">
      {/* Status Bar */}
      <div className="flex items-center justify-between bg-white rounded-xl border border-gray-200 px-5 py-3 shadow-sm">
        <div className="flex items-center gap-3">
          {isActive ? (
            <>
              <span className="w-2.5 h-2.5 rounded-full bg-green-500 animate-pulse" />
              <span className="text-sm font-semibold text-green-700">Session Active — Class: {classId}</span>
            </>
          ) : (
            <>
              <span className="w-2.5 h-2.5 rounded-full bg-gray-300" />
              <span className="text-sm text-gray-500">No active session</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className={backendOnline === true ? 'text-green-600' : backendOnline === false ? 'text-orange-500' : 'text-gray-400'}>
            {backendOnline === true ? '🟢 DeepFace backend online' : backendOnline === false ? '🟡 Backend offline (local fallback)' : '⚪ Checking backend…'}
          </span>
          {!isActive && (
            <button
              onClick={() => navigate('/')}
              className="px-3 py-1 bg-primary-600 text-white rounded-lg text-xs font-medium hover:bg-primary-700 transition-colors"
            >
              Start Session →
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Camera Feed */}
        <div className="xl:col-span-2 space-y-4">
          <div className="bg-black rounded-2xl overflow-hidden aspect-video relative">
            <video
              ref={videoRef}
              className="w-full h-full object-cover"
              autoPlay
              playsInline
              muted
            />
            {!cameraOn && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center text-gray-400">
                  <div className="text-6xl mb-3">📷</div>
                  <p className="text-sm">Camera is off</p>
                </div>
              </div>
            )}
            
            {showIntruderAlert && (
              <div className="absolute top-4 inset-x-0 mx-auto w-fit bg-red-600 border border-red-400 text-white font-bold px-6 py-2 rounded-full shadow-2xl animate-pulse flex items-center gap-2 z-50">
                <span className="text-xl">⚠️</span> UNKNOWN FACE DETECTED!
              </div>
            )}
            

            {capturing && (
              <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-red-600/90 text-white text-xs px-2 py-1 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                RECORDING · Every {captureInterval}s
              </div>
            )}
            {lastResult && capturing && (
              <div className="absolute bottom-3 left-3 right-3 bg-black/60 backdrop-blur-sm rounded-xl p-3 text-white text-xs">
                <div className="flex justify-between mb-1">
                  <span>Detected faces: <strong>{lastResult.facesTotal}</strong></span>
                  <span>Recognized: <strong>{lastResult.students.length}</strong></span>
                  <span>Unknown: <strong>{lastResult.unrecognized}</strong></span>
                </div>
                {lastResult.students.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {lastResult.students.map((s) => (
                      <span key={s.studentId} className="bg-white/20 rounded px-1.5 py-0.5 text-xs">
                        {s.name} — {s.emotion}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex flex-wrap items-center gap-3">
              {!cameraOn ? (
                <button
                  onClick={startCamera}
                  className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  📷 Start Camera
                </button>
              ) : (
                <button
                  onClick={stopCamera}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg text-sm font-medium transition-colors"
                >
                  ⏹ Stop Camera
                </button>
              )}

              {cameraOn && !capturing ? (
                <button
                  onClick={startCapturing}
                  disabled={!isActive}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors"
                >
                  ▶ Start Attendance Capture
                </button>
              ) : cameraOn && capturing ? (
                <button
                  onClick={stopCapturing}
                  className="flex items-center gap-2 px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  ⏸ Pause Capture
                </button>
              ) : null}

              {/* Interval selector */}
              <div className="flex items-center gap-2 ml-auto">
                <label className="text-xs text-gray-500">Capture every:</label>
                <select
                  value={captureInterval}
                  onChange={(e) => {
                    setCaptureInterval(Number(e.target.value))
                    if (capturing) { stopCapturing(); setTimeout(startCapturing, 100) }
                  }}
                  className="text-xs border border-gray-300 rounded-md px-2 py-1"
                >
                  {[3, 5, 10, 15, 30].map((v) => (
                    <option key={v} value={v}>{v}s</option>
                  ))}
                </select>
              </div>
            </div>

            {error && (
              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                ⚠ {error}
              </div>
            )}
          </div>

          {/* Detection Log */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-800">Detection Log</h3>
              <button onClick={() => setLogs([])} className="text-xs text-gray-400 hover:text-gray-600">
                Clear
              </button>
            </div>
            <div className="divide-y divide-gray-50 max-h-56 overflow-y-auto">
              {logs.length === 0 ? (
                <div className="px-4 py-6 text-center text-xs text-gray-400">
                  No detections yet. Start capture to begin.
                </div>
              ) : (
                logs.map((log, i) => (
                  <div key={i} className="px-4 py-2">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-mono text-gray-400">{log.ts}</span>
                      <span className={`text-xs ${log.backendOnline ? 'text-green-600' : 'text-orange-500'}`}>
                        {log.backendOnline ? 'DeepFace' : 'Local'}
                      </span>
                    </div>
                    {log.students.length === 0 ? (
                      <p className="text-xs text-gray-400">No students recognized ({log.facesTotal} face{log.facesTotal !== 1 ? 's' : ''} detected)</p>
                    ) : (
                      <div className="space-y-1">
                        {log.students.map((s) => (
                          <div key={s.studentId} className="flex items-center justify-between">
                            <span className="text-xs text-gray-700 font-medium">{s.name}</span>
                            <div className="flex items-center gap-2">
                              <EmotionBadge emotion={s.emotion} />
                              <span className={`text-xs font-medium ${engagementColor(s.engagement)}`}>
                                {s.engagement}
                              </span>
                              <span className="text-xs text-gray-400">{Math.round(s.confidence * 100)}%</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right Panel — Stats */}
        <div className="space-y-4">
          {/* Session Stats */}
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">Session Stats</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Recognized', value: attendeeCount, color: 'text-green-600' },
                { label: 'Samples', value: sampleCount, color: 'text-blue-600' },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-gray-50 rounded-lg p-3 text-center">
                  <p className={`text-2xl font-bold ${color}`}>{value}</p>
                  <p className="text-xs text-gray-500">{label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Emotion Summary */}
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-gray-800">Avg Emotion Analysis</h3>
              <span className="text-xs text-gray-400">{sampleCount} samples</span>
            </div>

            {sampleCount === 0 ? (
              <p className="text-xs text-gray-400 text-center py-4">No data yet</p>
            ) : (
              <div className="space-y-3">
                {emotionBars.map(({ key, label, color, value }) => (
                  <div key={key}>
                    <div className="flex justify-between text-xs text-gray-600 mb-1">
                      <span>{label}</span>
                      <span className="font-semibold">{value}%</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2.5">
                      <div
                        className={`${color} h-2.5 rounded-full transition-all duration-700`}
                        style={{ width: `${value}%` }}
                      />
                    </div>
                  </div>
                ))}
                <div className="pt-2 border-t border-gray-100">
                  <p className="text-xs text-center text-gray-600">
                    Dominant: <span className="font-semibold capitalize text-gray-900">{emotionSummary.dominant}</span>
                  </p>
                  <p className="text-xs text-center text-primary-600 font-semibold mt-1">
                    Engagement Score: {Math.round(emotionSummary.avgEngagementScore * 100)}%
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Present Students */}
          <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-800 mb-3">
              Present Students ({attendeeCount})
            </h3>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {attendeeCount === 0 ? (
                <p className="text-xs text-gray-400 text-center py-3">No students detected yet</p>
              ) : (
                Object.values(useSessionStore((s) => s.attendees)).map((a) => (
                  <div key={a.studentId} className="flex items-center justify-between py-1">
                    <div>
                      <p className="text-xs font-medium text-gray-800">{a.name}</p>
                      <p className="text-xs text-gray-400">{a.detectionCount}× detected</p>
                    </div>
                    <EmotionBadge emotion={a.emotions[a.emotions.length - 1] || 'neutral'} />
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Intruders Panel */}
          {unrecognizedIntruders && unrecognizedIntruders.length > 0 && (
            <div className="bg-white rounded-xl border border-red-200 p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-red-700 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-600 animate-ping" />
                Unknown Attendees ({unrecognizedIntruders.length})
              </h3>
              <div className="flex gap-2 overflow-x-auto pb-2 custom-scrollbar">
                {[...unrecognizedIntruders].reverse().map((intruder, idx) => (
                  <div key={idx} className="flex-shrink-0 w-20 h-24 bg-gray-100 rounded-lg overflow-hidden border border-red-100 shadow-sm relative group">
                    <img src={intruder.imageBase64} alt="Unknown" className="w-full h-full object-cover" />
                    <div className="absolute bottom-0 inset-x-0 bg-black/60 text-[10px] text-white p-1 truncate text-center">
                      {intruder.timestamp.split('T')[1].split('.')[0]}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Backend Info */}
          <div className="bg-gray-50 rounded-xl border border-gray-200 p-4">
            <h3 className="text-xs font-semibold text-gray-600 mb-2">Face Recognition Engine</h3>
            <div className="space-y-1 text-xs text-gray-500">
              <p>🧠 Model: Facenet512</p>
              <p>🔍 Detector: RetinaFace</p>
              <p>🎭 Emotion: DeepFace Analyze</p>
              <p className={backendOnline ? 'text-green-600' : 'text-orange-500'}>
                {backendOnline
                  ? '✅ Running on backend'
                  : '⚠ Fallback mode (start backend for full accuracy)'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

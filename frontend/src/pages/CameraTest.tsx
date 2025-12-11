import React, { useRef, useState, useEffect } from 'react'
import { CheckCircleIcon, XCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'

interface DiagnosticResult {
  name: string
  status: 'success' | 'error' | 'warning' | 'pending'
  message: string
}

export const CameraTest: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [error, setError] = useState<string>('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [diagnostics, setDiagnostics] = useState<DiagnosticResult[]>([])
  const [browserInfo, setBrowserInfo] = useState<string>('')
  const [permissionStatus, setPermissionStatus] = useState<string>('unknown')

  useEffect(() => {
    // Get browser info
    const userAgent = navigator.userAgent
    let browser = 'Unknown'
    if (userAgent.includes('Chrome')) browser = 'Chrome'
    else if (userAgent.includes('Firefox')) browser = 'Firefox'
    else if (userAgent.includes('Safari')) browser = 'Safari'
    else if (userAgent.includes('Edge')) browser = 'Edge'
    setBrowserInfo(browser)

    // Run initial diagnostics
    runDiagnostics()

    return () => {
      stopCamera()
    }
  }, [])

  const runDiagnostics = async () => {
    const results: DiagnosticResult[] = []

    // Check 1: MediaDevices API support
    if (navigator.mediaDevices && typeof navigator.mediaDevices.getUserMedia === 'function') {
      results.push({
        name: 'MediaDevices API',
        status: 'success',
        message: 'Browser supports camera access'
      })
    } else {
      results.push({
        name: 'MediaDevices API',
        status: 'error',
        message: 'Browser does not support camera access'
      })
    }

    // Check 2: HTTPS/Localhost
    const isSecure = window.location.protocol === 'https:' || window.location.hostname === 'localhost'
    results.push({
      name: 'Secure Context',
      status: isSecure ? 'success' : 'error',
      message: isSecure ? 'Running on secure context (HTTPS/localhost)' : 'Camera requires HTTPS or localhost'
    })

    // Check 3: Permission status (if supported)
    try {
      if (navigator.permissions) {
        const permission = await navigator.permissions.query({ name: 'camera' as PermissionName })
        setPermissionStatus(permission.state)
        results.push({
          name: 'Camera Permission',
          status: permission.state === 'granted' ? 'success' : permission.state === 'denied' ? 'error' : 'warning',
          message: `Permission status: ${permission.state}`
        })
      }
    } catch (e) {
      results.push({
        name: 'Camera Permission',
        status: 'warning',
        message: 'Permission status check not supported'
      })
    }

    // Check 4: Enumerate devices
    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      const videoDevices = devices.filter(device => device.kind === 'videoinput')
      results.push({
        name: 'Camera Devices',
        status: videoDevices.length > 0 ? 'success' : 'error',
        message: `Found ${videoDevices.length} camera device(s)`
      })
    } catch (e) {
      results.push({
        name: 'Camera Devices',
        status: 'error',
        message: 'Could not enumerate devices'
      })
    }

    setDiagnostics(results)
  }

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => {
        track.stop()
        console.log('Stopped track:', track.label)
      })
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setIsStreaming(false)
  }

  const startCamera = async () => {
    setError('')
    console.log('=== Starting Camera Test ===')
    console.log('Browser:', browserInfo)
    console.log('URL:', window.location.href)
    console.log('Protocol:', window.location.protocol)
    
    try {
      console.log('Requesting camera access...')
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        }
      })
      
      console.log('✅ Camera access granted!')
      console.log('Stream:', stream)
      console.log('Video tracks:', stream.getVideoTracks())
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        streamRef.current = stream
        
        videoRef.current.onloadedmetadata = () => {
          console.log('✅ Video metadata loaded')
          console.log('Video dimensions:', videoRef.current?.videoWidth, 'x', videoRef.current?.videoHeight)
          setIsStreaming(true)
          setError('')
        }

        videoRef.current.onerror = (e) => {
          console.error('❌ Video element error:', e)
          setError('Video element error occurred')
        }
      }
    } catch (err: any) {
      console.error('❌ Camera error:', err)
      console.error('Error name:', err.name)
      console.error('Error message:', err.message)
      
      let errorMessage = 'Camera error: '
      
      switch (err.name) {
        case 'NotAllowedError':
          errorMessage += 'Permission denied. Please allow camera access in your browser settings.'
          break
        case 'NotFoundError':
          errorMessage += 'No camera found. Please connect a camera and try again.'
          break
        case 'NotReadableError':
          errorMessage += 'Camera is already in use by another application. Please close other apps using the camera.'
          break
        case 'OverconstrainedError':
          errorMessage += 'Camera does not support the requested settings.'
          break
        case 'SecurityError':
          errorMessage += 'Camera access blocked due to security restrictions.'
          break
        default:
          errorMessage += `${err.name} - ${err.message}`
      }
      
      setError(errorMessage)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleIcon className="h-5 w-5 text-green-600" />
      case 'error':
        return <XCircleIcon className="h-5 w-5 text-red-600" />
      case 'warning':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600" />
      default:
        return <div className="h-5 w-5 border-2 border-gray-300 rounded-full animate-spin" />
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">🔧 Camera Diagnostic Test</h1>
          <p className="text-gray-600 mt-2">Test your camera and diagnose any issues</p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Camera Test */}
          <div className="lg:col-span-2">
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start">
                  <XCircleIcon className="h-5 w-5 text-red-600 mt-0.5 mr-2 flex-shrink-0" />
                  <div>
                    <p className="font-medium text-red-800">Camera Error</p>
                    <p className="text-sm text-red-600 mt-1">{error}</p>
                  </div>
                </div>
              </div>
            )}
            
            <div className="bg-white rounded-lg shadow-lg p-6">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-xl font-semibold">Camera Preview</h2>
                <div className="flex space-x-2">
                  {!isStreaming ? (
                    <button
                      onClick={startCamera}
                      className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                    >
                      Start Camera
                    </button>
                  ) : (
                    <button
                      onClick={stopCamera}
                      className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
                    >
                      Stop Camera
                    </button>
                  )}
                </div>
              </div>
              
              <div className="relative bg-gray-900 rounded-lg overflow-hidden" style={{ aspectRatio: '16/9' }}>
                {!isStreaming && (
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-white">
                    <svg className="h-24 w-24 mb-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <p className="text-lg">Click "Start Camera" to begin test</p>
                  </div>
                )}
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-full h-full object-cover"
                  style={{ display: isStreaming ? 'block' : 'none' }}
                />
              </div>
              
              {isStreaming && (
                <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <div className="flex items-center">
                    <CheckCircleIcon className="h-5 w-5 text-green-600 mr-2" />
                    <p className="text-green-800 font-medium">✅ Camera is working perfectly!</p>
                  </div>
                  <p className="text-sm text-green-700 mt-2">
                    Your camera is functioning correctly. You can now use it for student registration and attendance.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Diagnostics Panel */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
              <h3 className="text-lg font-semibold mb-4">System Diagnostics</h3>
              <div className="space-y-3">
                {diagnostics.map((diagnostic, index) => (
                  <div key={index} className="flex items-start">
                    <div className="flex-shrink-0 mt-0.5">
                      {getStatusIcon(diagnostic.status)}
                    </div>
                    <div className="ml-3 flex-1">
                      <p className="text-sm font-medium text-gray-900">{diagnostic.name}</p>
                      <p className="text-xs text-gray-600 mt-0.5">{diagnostic.message}</p>
                    </div>
                  </div>
                ))}
              </div>
              
              <button
                onClick={runDiagnostics}
                className="mt-4 w-full px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors"
              >
                Re-run Diagnostics
              </button>
            </div>

            <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
              <h3 className="text-lg font-semibold mb-3">System Info</h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="text-gray-600">Browser:</span>
                  <span className="ml-2 font-medium">{browserInfo}</span>
                </div>
                <div>
                  <span className="text-gray-600">Protocol:</span>
                  <span className="ml-2 font-medium">{window.location.protocol}</span>
                </div>
                <div>
                  <span className="text-gray-600">Host:</span>
                  <span className="ml-2 font-medium">{window.location.hostname}</span>
                </div>
                <div>
                  <span className="text-gray-600">Permission:</span>
                  <span className="ml-2 font-medium capitalize">{permissionStatus}</span>
                </div>
              </div>
            </div>
            
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">Quick Fixes</h3>
              <ul className="text-xs text-blue-800 space-y-1.5">
                <li>• Click the lock icon (🔒) in address bar</li>
                <li>• Set Camera permission to "Allow"</li>
                <li>• Close Zoom, Teams, or other camera apps</li>
                <li>• Try Chrome browser (recommended)</li>
                <li>• Hard refresh: Ctrl+Shift+R</li>
                <li>• Check console (F12) for errors</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Troubleshooting Guide */}
        <div className="mt-6 bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Troubleshooting Guide</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Chrome</h4>
              <ol className="text-sm text-gray-600 space-y-1 list-decimal list-inside">
                <li>Click lock icon (🔒) in address bar</li>
                <li>Click "Site settings"</li>
                <li>Find "Camera" and set to "Allow"</li>
                <li>Refresh the page</li>
              </ol>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Firefox</h4>
              <ol className="text-sm text-gray-600 space-y-1 list-decimal list-inside">
                <li>Click lock icon in address bar</li>
                <li>Click "Connection secure"</li>
                <li>Go to "Permissions" tab</li>
                <li>Allow "Use the Camera"</li>
              </ol>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Edge</h4>
              <ol className="text-sm text-gray-600 space-y-1 list-decimal list-inside">
                <li>Click lock icon in address bar</li>
                <li>Click "Permissions for this site"</li>
                <li>Set Camera to "Allow"</li>
                <li>Refresh the page</li>
              </ol>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Common Issues</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li>• Camera in use by another app</li>
                <li>• Permission denied in browser</li>
                <li>• No camera detected</li>
                <li>• Browser not supported</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

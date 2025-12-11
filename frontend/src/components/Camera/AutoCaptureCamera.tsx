import React, { useRef, useState, useCallback, useEffect } from 'react'
import { CameraIcon, XMarkIcon, PlayIcon, PauseIcon } from '@heroicons/react/24/outline'

interface AutoCaptureCameraProps {
  onCapture: (imageData: string) => void
  title?: string
  subtitle?: string
  captureInterval?: number // milliseconds between captures
}

export const AutoCaptureCamera: React.FC<AutoCaptureCameraProps> = ({
  onCapture,
  title = 'Auto Capture Camera',
  subtitle = 'Camera will automatically capture and process faces',
  captureInterval = 3000 // 3 seconds default
}) => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [isAutoCapturing, setIsAutoCapturing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  const [captureCount, setCaptureCount] = useState(0)

  const startCamera = useCallback(async () => {
    console.log('Starting camera...')
    setError(null)
    
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera API not supported in this browser')
      }

      console.log('Requesting camera access...')
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        }
      })
      
      console.log('Camera access granted!', stream)
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        streamRef.current = stream
        
        videoRef.current.onloadedmetadata = () => {
          console.log('Video metadata loaded')
          setIsStreaming(true)
          setError(null)
        }
      }
    } catch (err: any) {
      console.error('Error accessing camera:', err)
      let errorMessage = 'Unable to access camera. '
      
      if (err.name === 'NotAllowedError') {
        errorMessage += 'Permission denied. Please allow camera access in your browser settings.'
      } else if (err.name === 'NotFoundError') {
        errorMessage += 'No camera found. Please connect a camera and try again.'
      } else if (err.name === 'NotReadableError') {
        errorMessage += 'Camera is already in use by another application.'
      } else {
        errorMessage += err.message || 'Please check your camera and try again.'
      }
      
      setError(errorMessage)
    }
  }, [])

  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setIsStreaming(false)
    stopAutoCapture()
  }, [])

  const capturePhoto = useCallback(() => {
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current
      const canvas = canvasRef.current
      
      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      
      const context = canvas.getContext('2d')
      if (context) {
        context.drawImage(video, 0, 0, canvas.width, canvas.height)
        const imageData = canvas.toDataURL('image/jpeg', 0.9)
        const base64Data = imageData.split(',')[1]
        
        setCaptureCount(prev => prev + 1)
        onCapture(base64Data)
      }
    }
  }, [onCapture])

  const startAutoCapture = useCallback(() => {
    if (!isStreaming) return
    
    setIsAutoCapturing(true)
    setCaptureCount(0)
    
    // Capture immediately
    capturePhoto()
    
    // Then capture at intervals
    intervalRef.current = setInterval(() => {
      capturePhoto()
    }, captureInterval)
  }, [isStreaming, capturePhoto, captureInterval])

  const stopAutoCapture = useCallback(() => {
    setIsAutoCapturing(false)
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  useEffect(() => {
    return () => {
      stopCamera()
    }
  }, [stopCamera])

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="mb-4">
        <h3 className="text-xl font-semibold text-gray-900">{title}</h3>
        <p className="text-sm text-gray-600 mt-1">{subtitle}</p>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <div className="relative bg-gray-900 rounded-lg overflow-hidden" style={{ aspectRatio: '16/9' }}>
        {!isStreaming && (
          <div className="absolute inset-0 flex items-center justify-center">
            <button
              onClick={startCamera}
              className="flex flex-col items-center space-y-3 text-white hover:text-primary-400 transition-colors"
            >
              <CameraIcon className="h-16 w-16" />
              <span className="text-lg font-medium">Start Camera</span>
            </button>
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

        <canvas ref={canvasRef} className="hidden" />

        {/* Face guide overlay */}
        {isStreaming && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-64 h-80 border-4 border-primary-500 rounded-full opacity-50"></div>
          </div>
        )}

        {/* Auto-capture indicator */}
        {isAutoCapturing && (
          <div className="absolute top-4 right-4 bg-red-600 text-white px-3 py-1 rounded-full flex items-center space-x-2">
            <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
            <span className="text-sm font-medium">AUTO CAPTURING</span>
          </div>
        )}

        {/* Capture count */}
        {isAutoCapturing && captureCount > 0 && (
          <div className="absolute bottom-4 left-4 bg-black bg-opacity-70 text-white px-3 py-1 rounded">
            <span className="text-sm">Captures: {captureCount}</span>
          </div>
        )}
      </div>

      <div className="mt-6 flex justify-center space-x-4">
        {!isStreaming ? (
          <button
            onClick={startCamera}
            className="flex items-center px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
          >
            <CameraIcon className="h-5 w-5 mr-2" />
            Start Camera
          </button>
        ) : (
          <>
            {!isAutoCapturing ? (
              <button
                onClick={startAutoCapture}
                className="flex items-center px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
              >
                <PlayIcon className="h-5 w-5 mr-2" />
                Start Auto Capture
              </button>
            ) : (
              <button
                onClick={stopAutoCapture}
                className="flex items-center px-6 py-3 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors"
              >
                <PauseIcon className="h-5 w-5 mr-2" />
                Pause Auto Capture
              </button>
            )}
            <button
              onClick={stopCamera}
              className="flex items-center px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
            >
              <XMarkIcon className="h-5 w-5 mr-2" />
              Stop Camera
            </button>
          </>
        )}
      </div>

      {isAutoCapturing && (
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">
            📸 Camera is automatically capturing every {captureInterval / 1000} seconds
          </p>
        </div>
      )}
    </div>
  )
}

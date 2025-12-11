import React, { useRef, useState, useCallback } from 'react'
import { CameraIcon, XMarkIcon, CheckIcon } from '@heroicons/react/24/outline'

interface WebcamCaptureProps {
  onCapture: (imageData: string) => void
  onCancel?: () => void
  title?: string
  subtitle?: string
}

export const WebcamCapture: React.FC<WebcamCaptureProps> = ({
  onCapture,
  onCancel,
  title = 'Capture Photo',
  subtitle = 'Position your face in the frame'
}) => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [capturedImage, setCapturedImage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const startCamera = useCallback(async () => {
    console.log('Starting camera...')
    setError(null)
    
    try {
      // Check if mediaDevices is available
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
        
        // Wait for video to be ready
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
        setCapturedImage(imageData)
        stopCamera()
      }
    }
  }, [stopCamera])

  const retake = useCallback(() => {
    setCapturedImage(null)
    startCamera()
  }, [startCamera])

  const confirmCapture = useCallback(() => {
    if (capturedImage) {
      // Remove the data:image/jpeg;base64, prefix
      const base64Data = capturedImage.split(',')[1]
      onCapture(base64Data)
      setCapturedImage(null)
    }
  }, [capturedImage, onCapture])

  const handleCancel = useCallback(() => {
    stopCamera()
    setCapturedImage(null)
    if (onCancel) {
      onCancel()
    }
  }, [stopCamera, onCancel])

  React.useEffect(() => {
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
        {!isStreaming && !capturedImage && (
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

        {capturedImage ? (
          <img
            src={capturedImage}
            alt="Captured"
            className="w-full h-full object-cover"
          />
        ) : (
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            className="w-full h-full object-cover"
            style={{ display: isStreaming ? 'block' : 'none' }}
          />
        )}

        <canvas ref={canvasRef} className="hidden" />

        {/* Face guide overlay */}
        {isStreaming && !capturedImage && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="w-64 h-80 border-4 border-primary-500 rounded-full opacity-50"></div>
          </div>
        )}
      </div>

      <div className="mt-6 flex justify-center space-x-4">
        {!capturedImage && isStreaming && (
          <>
            <button
              onClick={capturePhoto}
              className="flex items-center px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
            >
              <CameraIcon className="h-5 w-5 mr-2" />
              Capture Photo
            </button>
            <button
              onClick={handleCancel}
              className="flex items-center px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
            >
              <XMarkIcon className="h-5 w-5 mr-2" />
              Cancel
            </button>
          </>
        )}

        {capturedImage && (
          <>
            <button
              onClick={confirmCapture}
              className="flex items-center px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
            >
              <CheckIcon className="h-5 w-5 mr-2" />
              Confirm
            </button>
            <button
              onClick={retake}
              className="flex items-center px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
            >
              <CameraIcon className="h-5 w-5 mr-2" />
              Retake
            </button>
          </>
        )}
      </div>
    </div>
  )
}

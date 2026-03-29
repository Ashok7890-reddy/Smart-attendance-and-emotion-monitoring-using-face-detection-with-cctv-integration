import React, { useEffect, useState } from 'react'
import { enhancedFaceService } from '@/services/enhancedFaceService'

interface FaceServiceInitializerProps {
  children: React.ReactNode
}

export const FaceServiceInitializer: React.FC<FaceServiceInitializerProps> = ({ children }) => {
  const [isInitialized, setIsInitialized] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [initializationDetails, setInitializationDetails] = useState<any>(null)

  useEffect(() => {
    initializeFaceService()
  }, [])

  const initializeFaceService = async () => {
    try {
      console.log('🚀 Initializing Enhanced Face Recognition Service...')
      setIsLoading(true)
      setError(null)

      const startTime = performance.now()
      
      // Initialize the enhanced face service
      await enhancedFaceService.loadModels()
      
      const endTime = performance.now()
      const initTime = endTime - startTime

      // Get system capabilities
      const stats = enhancedFaceService.getPerformanceStats()
      const isHighAccuracyAvailable = enhancedFaceService.isHighAccuracyAvailable()

      const details = {
        initializationTime: initTime,
        highAccuracyAvailable: isHighAccuracyAvailable,
        currentMode: stats?.currentMode || 'Unknown',
        systemReady: true
      }

      setInitializationDetails(details)
      setIsInitialized(true)

      console.log('✅ Enhanced Face Recognition Service initialized successfully!')
      console.log('🎯 High accuracy mode:', isHighAccuracyAvailable ? 'Available' : 'Not Available')
      console.log('📊 Current mode:', details.currentMode)
      console.log('⚡ Initialization time:', initTime.toFixed(1) + 'ms')

    } catch (err: any) {
      console.error('❌ Failed to initialize Enhanced Face Recognition Service:', err)
      setError(err.message || 'Failed to initialize face recognition system')
      
      // Still allow the app to load with degraded functionality
      setIsInitialized(true)
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Initializing Face Recognition
          </h2>
          <p className="text-gray-600 mb-4">
            Loading enhanced face recognition models...
          </p>
          <div className="text-sm text-gray-500">
            This may take a few moments on first load
          </div>
        </div>
      </div>
    )
  }

  if (error && !isInitialized) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Initialization Failed
          </h2>
          <p className="text-gray-600 mb-4">
            {error}
          </p>
          <button
            onClick={initializeFaceService}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
          >
            Retry Initialization
          </button>
        </div>
      </div>
    )
  }

  // Show initialization success notification briefly
  if (isInitialized && initializationDetails && !error) {
    return (
      <>
        {children}
        <InitializationNotification details={initializationDetails} />
      </>
    )
  }

  return <>{children}</>
}

interface InitializationNotificationProps {
  details: any
}

const InitializationNotification: React.FC<InitializationNotificationProps> = ({ details }) => {
  const [show, setShow] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => setShow(false), 5000) // Hide after 5 seconds
    return () => clearTimeout(timer)
  }, [])

  if (!show) return null

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm">
      <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3 w-0 flex-1">
            <p className="text-sm font-medium text-gray-900">
              Face Recognition Ready
            </p>
            <p className="mt-1 text-sm text-gray-500">
              {details.highAccuracyAvailable ? 'High accuracy mode enabled' : 'Standard mode active'}
            </p>
            <div className="mt-2 text-xs text-gray-400">
              Initialized in {details.initializationTime.toFixed(1)}ms
            </div>
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              onClick={() => setShow(false)}
              className="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500"
            >
              <span className="sr-only">Close</span>
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
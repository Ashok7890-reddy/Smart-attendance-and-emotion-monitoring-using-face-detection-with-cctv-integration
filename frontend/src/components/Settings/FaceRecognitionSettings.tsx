import React, { useState, useEffect } from 'react'
import { CogIcon, EyeIcon, ChartBarIcon, BeakerIcon } from '@heroicons/react/24/outline'
import { enhancedFaceService } from '@/services/enhancedFaceService'

export const FaceRecognitionSettings: React.FC = () => {
  const [stats, setStats] = useState<any>(null)
  const [preferHighAccuracy, setPreferHighAccuracy] = useState(true)
  const [loading, setLoading] = useState(false)
  const [testResults, setTestResults] = useState<any>(null)

  useEffect(() => {
    loadStats()
    const interval = setInterval(loadStats, 5000) // Update every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const loadStats = () => {
    const currentStats = enhancedFaceService.getPerformanceStats()
    setStats(currentStats)
  }

  const handlePreferenceChange = (prefer: boolean) => {
    setPreferHighAccuracy(prefer)
    enhancedFaceService.setPreferHighAccuracy(prefer)
    console.log(`🔧 High accuracy preference: ${prefer ? 'Enabled' : 'Disabled'}`)
  }

  const runSystemTest = async () => {
    setLoading(true)
    setTestResults(null)

    try {
      // Create test canvas
      const canvas = document.createElement('canvas')
      canvas.width = 640
      canvas.height = 480
      const ctx = canvas.getContext('2d')!
      
      // Draw test pattern
      ctx.fillStyle = '#f0f0f0'
      ctx.fillRect(0, 0, 640, 480)
      ctx.fillStyle = '#d0d0d0'
      ctx.fillRect(200, 150, 240, 180) // Face area
      ctx.fillStyle = '#333'
      ctx.fillRect(230, 180, 20, 20) // Left eye
      ctx.fillRect(390, 180, 20, 20) // Right eye
      ctx.fillRect(310, 220, 20, 30) // Nose
      ctx.fillRect(290, 270, 60, 10) // Mouth

      const startTime = performance.now()
      const detection = await enhancedFaceService.detectFace(canvas)
      const endTime = performance.now()

      const results = {
        success: !!detection,
        processingTime: endTime - startTime,
        modelUsed: detection?.modelUsed || 'None',
        embeddingDimension: detection?.embeddingDimension || 0,
        confidence: detection?.detection?.score || 0,
        systemStats: enhancedFaceService.getPerformanceStats()
      }

      setTestResults(results)
    } catch (error) {
      setTestResults({
        success: false,
        error: error.message,
        systemStats: enhancedFaceService.getPerformanceStats()
      })
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'High': return 'text-green-600 bg-green-100'
      case 'Medium': return 'text-yellow-600 bg-yellow-100'
      case 'Standard': return 'text-blue-600 bg-blue-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const getSpeedColor = (speed: string) => {
    switch (speed) {
      case 'Fast': return 'text-green-600 bg-green-100'
      case 'Medium': return 'text-yellow-600 bg-yellow-100'
      case 'Slow': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center mb-6">
          <CogIcon className="h-6 w-6 text-primary-600 mr-3" />
          <h2 className="text-xl font-semibold text-gray-900">Face Recognition Configuration</h2>
        </div>

        {/* System Status */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">Current Mode</span>
              <EyeIcon className="h-5 w-5 text-gray-400" />
            </div>
            <p className="text-lg font-semibold text-gray-900 mt-1">
              {stats?.currentMode || 'Loading...'}
            </p>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">Accuracy Level</span>
              <ChartBarIcon className="h-5 w-5 text-gray-400" />
            </div>
            <div className="mt-1">
              <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(stats?.summary?.accuracy)}`}>
                {stats?.summary?.accuracy || 'Unknown'}
              </span>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">Processing Speed</span>
              <BeakerIcon className="h-5 w-5 text-gray-400" />
            </div>
            <div className="mt-1">
              <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getSpeedColor(stats?.summary?.speed)}`}>
                {stats?.summary?.speed || 'Unknown'}
              </span>
            </div>
          </div>
        </div>

        {/* Model Preferences */}
        <div className="border-t pt-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Model Preferences</h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-sm font-medium text-gray-700">
                  Prefer High Accuracy Mode (ONNX)
                </label>
                <p className="text-sm text-gray-500">
                  Use ONNX models when available for 95-99% accuracy with 512D embeddings
                </p>
              </div>
              <button
                onClick={() => handlePreferenceChange(!preferHighAccuracy)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  preferHighAccuracy ? 'bg-primary-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    preferHighAccuracy ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-blue-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h4 className="text-sm font-medium text-blue-800">
                    High Accuracy Mode {enhancedFaceService.isHighAccuracyAvailable() ? 'Available' : 'Unavailable'}
                  </h4>
                  <p className="text-sm text-blue-700 mt-1">
                    {enhancedFaceService.isHighAccuracyAvailable() 
                      ? 'ONNX models are loaded and ready for high-accuracy recognition.'
                      : 'ONNX models are not available. Using standard face-api.js models.'
                    }
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Performance Statistics */}
        {stats && (
          <div className="border-t pt-6 mt-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Performance Statistics</h3>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-primary-600">
                  {stats.totalDetections || 0}
                </div>
                <div className="text-sm text-gray-600">Total Processed</div>
              </div>
              
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {stats.accuracyRate?.toFixed(1) || 0}%
                </div>
                <div className="text-sm text-gray-600">High Accuracy Usage</div>
              </div>
              
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {stats.averageProcessingTime?.toFixed(1) || 0}ms
                </div>
                <div className="text-sm text-gray-600">Avg Processing Time</div>
              </div>
              
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {stats.summary?.reliability || 'Unknown'}
                </div>
                <div className="text-sm text-gray-600">System Reliability</div>
              </div>
            </div>

            {/* Model Usage Breakdown */}
            <div className="mt-6">
              <h4 className="text-sm font-medium text-gray-700 mb-3">Model Usage Distribution</h4>
              <div className="space-y-2">
                <div className="flex items-center">
                  <div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div>
                  <span className="text-sm text-gray-600">
                    High Accuracy (ONNX): {stats.highAccuracyUsage || 0} detections
                  </span>
                </div>
                <div className="flex items-center">
                  <div className="w-3 h-3 bg-blue-500 rounded-full mr-2"></div>
                  <span className="text-sm text-gray-600">
                    Standard (face-api.js): {stats.standardUsage || 0} detections
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* System Test */}
        <div className="border-t pt-6 mt-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900">System Test</h3>
            <button
              onClick={runSystemTest}
              disabled={loading}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-400 text-white rounded-lg transition-colors"
            >
              {loading ? 'Testing...' : 'Run Test'}
            </button>
          </div>

          {testResults && (
            <div className={`p-4 rounded-lg ${testResults.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              <h4 className={`font-medium ${testResults.success ? 'text-green-800' : 'text-red-800'}`}>
                {testResults.success ? '✅ System Test Passed' : '❌ System Test Failed'}
              </h4>
              <div className="mt-2 text-sm">
                {testResults.success ? (
                  <div className="space-y-1">
                    <p><strong>Model Used:</strong> {testResults.modelUsed}</p>
                    <p><strong>Processing Time:</strong> {testResults.processingTime.toFixed(1)}ms</p>
                    <p><strong>Embedding Dimension:</strong> {testResults.embeddingDimension}D</p>
                    <p><strong>Detection Confidence:</strong> {(testResults.confidence * 100).toFixed(1)}%</p>
                  </div>
                ) : (
                  <p className="text-red-700">Error: {testResults.error}</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="border-t pt-6 mt-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h3>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => window.open('/setup-onnx-models.html', '_blank')}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Setup ONNX Models
            </button>
            <button
              onClick={() => window.open('/onnx-performance-monitor.html', '_blank')}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
            >
              Performance Monitor
            </button>
            <button
              onClick={() => window.open('/performance-monitor.html', '_blank')}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
            >
              Legacy Monitor
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
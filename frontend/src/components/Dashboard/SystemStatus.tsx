import React, { useState, useEffect } from 'react'
import { EyeIcon, CpuChipIcon, ClockIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'
import { enhancedFaceService } from '@/services/enhancedFaceService'

export const SystemStatus: React.FC = () => {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
    const interval = setInterval(loadStats, 10000) // Update every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const loadStats = () => {
    try {
      const currentStats = enhancedFaceService.getPerformanceStats()
      setStats(currentStats)
    } catch (error) {
      console.error('Failed to load system stats:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'High':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'Medium':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      default:
        return <ExclamationTriangleIcon className="h-5 w-5 text-gray-500" />
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

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-3 bg-gray-200 rounded"></div>
            <div className="h-3 bg-gray-200 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">System Status</h3>
        <button
          onClick={loadStats}
          className="text-sm text-primary-600 hover:text-primary-700 font-medium"
        >
          Refresh
        </button>
      </div>

      {/* Overall System Health */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Face Recognition System</span>
          {stats?.hybridAvailable ? (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
              <CheckCircleIcon className="h-3 w-3 mr-1" />
              Operational
            </span>
          ) : (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
              <ExclamationTriangleIcon className="h-3 w-3 mr-1" />
              Limited
            </span>
          )}
        </div>
        <p className="text-sm text-gray-600">
          {stats?.currentMode || 'System initializing...'}
        </p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center">
            <EyeIcon className="h-5 w-5 text-gray-400 mr-2" />
            <div>
              <p className="text-sm font-medium text-gray-900">
                {stats?.totalDetections || 0}
              </p>
              <p className="text-xs text-gray-600">Total Processed</p>
            </div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <div className="flex items-center">
            <ClockIcon className="h-5 w-5 text-gray-400 mr-2" />
            <div>
              <p className="text-sm font-medium text-gray-900">
                {stats?.averageProcessingTime?.toFixed(1) || 0}ms
              </p>
              <p className="text-xs text-gray-600">Avg Processing</p>
            </div>
          </div>
        </div>
      </div>

      {/* Performance Indicators */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            {getStatusIcon(stats?.summary?.accuracy)}
            <span className="ml-2 text-sm text-gray-700">Accuracy Level</span>
          </div>
          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(stats?.summary?.accuracy)}`}>
            {stats?.summary?.accuracy || 'Unknown'}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <CpuChipIcon className="h-5 w-5 text-gray-500" />
            <span className="ml-2 text-sm text-gray-700">Processing Speed</span>
          </div>
          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(stats?.summary?.speed)}`}>
            {stats?.summary?.speed || 'Unknown'}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <CheckCircleIcon className="h-5 w-5 text-gray-500" />
            <span className="ml-2 text-sm text-gray-700">System Reliability</span>
          </div>
          <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(stats?.summary?.reliability)}`}>
            {stats?.summary?.reliability || 'Unknown'}
          </span>
        </div>
      </div>

      {/* Model Usage */}
      {stats && stats.totalDetections > 0 && (
        <div className="mt-6 pt-6 border-t border-gray-200">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Model Usage</h4>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600">High Accuracy (ONNX)</span>
              <span className="font-medium text-green-600">
                {stats.accuracyRate?.toFixed(1) || 0}%
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-green-500 h-2 rounded-full transition-all duration-300"
                style={{ width: `${stats.accuracyRate || 0}%` }}
              ></div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="mt-6 pt-6 border-t border-gray-200">
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => window.open('/onnx-performance-monitor.html', '_blank')}
            className="text-xs px-3 py-1 bg-primary-100 text-primary-700 rounded-full hover:bg-primary-200 transition-colors"
          >
            Performance Monitor
          </button>
          <button
            onClick={() => window.open('/setup-onnx-models.html', '_blank')}
            className="text-xs px-3 py-1 bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
          >
            Setup Models
          </button>
        </div>
      </div>
    </div>
  )
}
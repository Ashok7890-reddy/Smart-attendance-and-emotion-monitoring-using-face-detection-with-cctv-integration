import React from 'react'
import { useEmotionAnalytics } from '@/hooks/useEmotionAnalytics'
import { EmotionPieChart } from './EmotionPieChart'
import { EngagementTrendChart } from './EngagementTrendChart'
import { EmotionMetrics } from './EmotionMetrics'

interface EmotionDashboardProps {
  sessionId?: string
  className?: string
}

export const EmotionDashboard: React.FC<EmotionDashboardProps> = ({ 
  sessionId, 
  className = '' 
}) => {
  const {
    currentEmotions,
    emotionHistory,
    isLoading,
    engagementTrend,
    averageEngagement,
    hasData
  } = useEmotionAnalytics(sessionId)

  if (isLoading) {
    return (
      <div className={`space-y-6 ${className}`}>
        <div className="animate-pulse">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="card">
              <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
              <div className="h-64 bg-gray-200 rounded"></div>
            </div>
            <div className="card">
              <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
              <div className="h-64 bg-gray-200 rounded"></div>
            </div>
          </div>
          <div className="card">
            <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
            <div className="h-48 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    )
  }

  if (!hasData || !currentEmotions) {
    return (
      <div className={`${className}`}>
        <div className="card text-center py-12">
          <div className="text-gray-400 mb-4">
            <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">
            No Emotion Data Available
          </h3>
          <p className="text-gray-600">
            Start an attendance session to begin tracking student emotions and engagement levels.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Current Emotion Metrics */}
      <EmotionMetrics
        currentEmotions={currentEmotions}
        averageEngagement={averageEngagement}
        engagementTrend={engagementTrend}
      />

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Emotion Distribution Pie Chart */}
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">
              Current Emotion Distribution
            </h3>
            <div className="flex items-center text-sm text-gray-500">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-2"></div>
              Live
            </div>
          </div>
          <div className="h-64">
            <EmotionPieChart emotions={currentEmotions} />
          </div>
        </div>

        {/* Engagement Trend Chart */}
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold text-gray-900">
              Engagement Trends
            </h3>
            <div className="text-sm text-gray-500">
              Last {emotionHistory.length} updates
            </div>
          </div>
          <div className="h-64">
            <EngagementTrendChart emotionHistory={emotionHistory} />
          </div>
        </div>
      </div>

      {/* Insights and Recommendations */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Insights & Recommendations
        </h3>
        <div className="space-y-3">
          {currentEmotions.engagementScore < 50 && (
            <div className="flex items-start space-x-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="w-5 h-5 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-red-600 text-xs">!</span>
              </div>
              <div>
                <p className="text-sm font-medium text-red-800">Low Engagement Alert</p>
                <p className="text-sm text-red-700">
                  Consider taking a break, asking questions, or changing the teaching approach to re-engage students.
                </p>
              </div>
            </div>
          )}
          
          {currentEmotions.confused > 30 && (
            <div className="flex items-start space-x-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <div className="w-5 h-5 bg-yellow-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-yellow-600 text-xs">?</span>
              </div>
              <div>
                <p className="text-sm font-medium text-yellow-800">High Confusion Detected</p>
                <p className="text-sm text-yellow-700">
                  Many students appear confused. Consider reviewing the current topic or asking for questions.
                </p>
              </div>
            </div>
          )}
          
          {currentEmotions.interested > 70 && (
            <div className="flex items-start space-x-3 p-3 bg-green-50 border border-green-200 rounded-lg">
              <div className="w-5 h-5 bg-green-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-green-600 text-xs">✓</span>
              </div>
              <div>
                <p className="text-sm font-medium text-green-800">High Interest Level</p>
                <p className="text-sm text-green-700">
                  Students are highly engaged! This is a great time to introduce more complex concepts.
                </p>
              </div>
            </div>
          )}
          
          {engagementTrend > 5 && (
            <div className="flex items-start space-x-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-blue-600 text-xs">↗</span>
              </div>
              <div>
                <p className="text-sm font-medium text-blue-800">Improving Engagement</p>
                <p className="text-sm text-blue-700">
                  Engagement is trending upward. Keep up the current teaching approach!
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
import React from 'react'
import { 
  FaceSmileIcon, 
  FaceFrownIcon, 
  QuestionMarkCircleIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  MinusIcon
} from '@heroicons/react/24/outline'
import { EmotionStatistics } from '@/types'

interface EmotionMetricsProps {
  currentEmotions: EmotionStatistics
  averageEngagement: number
  engagementTrend: number
  className?: string
}

export const EmotionMetrics: React.FC<EmotionMetricsProps> = ({
  currentEmotions,
  averageEngagement,
  engagementTrend,
  className = ''
}) => {
  const getTrendIcon = (trend: number) => {
    if (trend > 2) return ArrowTrendingUpIcon
    if (trend < -2) return ArrowTrendingDownIcon
    return MinusIcon
  }

  const getTrendColor = (trend: number) => {
    if (trend > 2) return 'text-green-600'
    if (trend < -2) return 'text-red-600'
    return 'text-gray-600'
  }

  const getTrendText = (trend: number) => {
    if (trend > 2) return `+${trend.toFixed(1)}%`
    if (trend < -2) return `${trend.toFixed(1)}%`
    return 'No change'
  }

  const metrics = [
    {
      name: 'Interested',
      value: `${currentEmotions.interested}%`,
      icon: FaceSmileIcon,
      color: 'text-green-600',
      bgColor: 'bg-green-50',
      borderColor: 'border-green-200'
    },
    {
      name: 'Bored',
      value: `${currentEmotions.bored}%`,
      icon: FaceFrownIcon,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50',
      borderColor: 'border-yellow-200'
    },
    {
      name: 'Confused',
      value: `${currentEmotions.confused}%`,
      icon: QuestionMarkCircleIcon,
      color: 'text-red-600',
      bgColor: 'bg-red-50',
      borderColor: 'border-red-200'
    }
  ]

  const TrendIcon = getTrendIcon(engagementTrend)

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Current Emotion Breakdown */}
      <div className="grid grid-cols-3 gap-4">
        {metrics.map((metric) => (
          <div
            key={metric.name}
            className={`p-4 rounded-lg border ${metric.bgColor} ${metric.borderColor}`}
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{metric.name}</p>
                <p className="text-xl font-bold text-gray-900 mt-1">{metric.value}</p>
              </div>
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${metric.bgColor}`}>
                <metric.icon className={`h-6 w-6 ${metric.color}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Engagement Summary */}
      <div className="grid grid-cols-2 gap-4">
        <div className="card bg-blue-50 border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Current Engagement</p>
              <p className="text-2xl font-bold text-blue-900 mt-1">
                {currentEmotions.engagementScore}%
              </p>
            </div>
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
              <span className="text-blue-600 font-bold text-lg">
                {currentEmotions.engagementScore}
              </span>
            </div>
          </div>
        </div>

        <div className="card bg-gray-50 border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Average Engagement</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {averageEngagement}%
              </p>
              <div className={`flex items-center mt-1 text-sm ${getTrendColor(engagementTrend)}`}>
                <TrendIcon className="h-4 w-4 mr-1" />
                <span>{getTrendText(engagementTrend)}</span>
              </div>
            </div>
            <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center">
              <span className="text-gray-600 font-bold text-lg">
                {averageEngagement}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Engagement Level Indicator */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-gray-900">Engagement Level</h4>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
            currentEmotions.engagementScore >= 80 
              ? 'bg-green-100 text-green-800'
              : currentEmotions.engagementScore >= 60
              ? 'bg-yellow-100 text-yellow-800'
              : 'bg-red-100 text-red-800'
          }`}>
            {currentEmotions.engagementScore >= 80 
              ? 'High'
              : currentEmotions.engagementScore >= 60
              ? 'Medium'
              : 'Low'
            }
          </span>
        </div>
        
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${
              currentEmotions.engagementScore >= 80
                ? 'bg-green-500'
                : currentEmotions.engagementScore >= 60
                ? 'bg-yellow-500'
                : 'bg-red-500'
            }`}
            style={{ width: `${currentEmotions.engagementScore}%` }}
          />
        </div>
        
        <div className="flex justify-between text-xs text-gray-500 mt-2">
          <span>0%</span>
          <span>50%</span>
          <span>100%</span>
        </div>
      </div>
    </div>
  )
}
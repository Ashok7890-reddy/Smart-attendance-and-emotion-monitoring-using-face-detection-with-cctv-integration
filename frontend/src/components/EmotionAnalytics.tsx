import React, { useEffect, useState } from 'react'
import { FaceSmileIcon, ChartBarIcon } from '@heroicons/react/24/outline'

interface EmotionData {
  emotion: string
  count: number
  percentage: number
  emoji: string
  color: string
}

interface EngagementData {
  level: string
  count: number
  percentage: number
  emoji: string
  color: string
  bgColor: string
}

interface EmotionAnalyticsProps {
  entries: Array<{
    emotion?: string
    engagement?: string
    engagement_score?: number
    emotion_breakdown?: any
  }>
}

export const EmotionAnalytics: React.FC<EmotionAnalyticsProps> = ({ entries }) => {
  const [lastUpdateTime, setLastUpdateTime] = useState(Date.now())
  
  // Force re-render when entries change
  useEffect(() => {
    setLastUpdateTime(Date.now())
    console.log('📊 EmotionAnalytics entries updated:', entries.length)
  }, [entries])
  
  // Debug logging
  console.log('📊 EmotionAnalytics received entries:', entries.length)
  console.log('📊 Sample entries:', entries.slice(0, 3))
  
  // Calculate emotion distribution
  const emotionCounts: { [key: string]: number } = {}
  const engagementCounts: { [key: string]: number } = {}
  
  entries.forEach(entry => {
    if (entry.emotion) {
      emotionCounts[entry.emotion] = (emotionCounts[entry.emotion] || 0) + 1
      console.log(`📊 Counting emotion: ${entry.emotion}`)
    }
    if (entry.engagement) {
      engagementCounts[entry.engagement] = (engagementCounts[entry.engagement] || 0) + 1
      console.log(`📊 Counting engagement: ${entry.engagement}`)
    }
  })

  console.log('📊 Final emotion counts:', emotionCounts)
  console.log('📊 Final engagement counts:', engagementCounts)

  const total = entries.length

  const emotionData: EmotionData[] = [
    { emotion: 'happy', count: emotionCounts['happy'] || 0, percentage: 0, emoji: '😊', color: 'text-green-600' },
    { emotion: 'neutral', count: emotionCounts['neutral'] || 0, percentage: 0, emoji: '😐', color: 'text-gray-600' },
    { emotion: 'surprised', count: emotionCounts['surprised'] || 0, percentage: 0, emoji: '😲', color: 'text-blue-600' },
    { emotion: 'sad', count: emotionCounts['sad'] || 0, percentage: 0, emoji: '😢', color: 'text-indigo-600' },
    { emotion: 'angry', count: emotionCounts['angry'] || 0, percentage: 0, emoji: '😠', color: 'text-red-600' },
    { emotion: 'fearful', count: emotionCounts['fearful'] || 0, percentage: 0, emoji: '😨', color: 'text-orange-600' },
    { emotion: 'disgusted', count: emotionCounts['disgusted'] || 0, percentage: 0, emoji: '🤢', color: 'text-purple-600' },
  ].map(item => ({
    ...item,
    percentage: total > 0 ? Math.round((item.count / total) * 100) : 0
  }))

  const engagementData: EngagementData[] = [
    { 
      level: 'interested', 
      count: engagementCounts['interested'] || 0, 
      percentage: 0, 
      emoji: '😊', 
      color: 'text-green-700',
      bgColor: 'bg-green-500'
    },
    { 
      level: 'bored', 
      count: engagementCounts['bored'] || 0, 
      percentage: 0, 
      emoji: '😐', 
      color: 'text-yellow-700',
      bgColor: 'bg-yellow-500'
    },
    { 
      level: 'confused', 
      count: engagementCounts['confused'] || 0, 
      percentage: 0, 
      emoji: '😕', 
      color: 'text-orange-700',
      bgColor: 'bg-orange-500'
    },
    { 
      level: 'sleepy', 
      count: engagementCounts['sleepy'] || 0, 
      percentage: 0, 
      emoji: '😴', 
      color: 'text-red-700',
      bgColor: 'bg-red-500'
    },
  ].map(item => ({
    ...item,
    percentage: total > 0 ? Math.round((item.count / total) * 100) : 0
  }))

  // Calculate overall engagement score (0-100)
  const engagementScore = total > 0 
    ? Math.round(
        ((engagementCounts['interested'] || 0) * 100 + 
         (engagementCounts['bored'] || 0) * 40 + 
         (engagementCounts['confused'] || 0) * 20 + 
         (engagementCounts['sleepy'] || 0) * 0) / total
      )
    : 0

  const getScoreColor = (score: number) => {
    if (score >= 75) return 'text-green-600'
    if (score >= 50) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreBg = (score: number) => {
    if (score >= 75) return 'bg-green-100'
    if (score >= 50) return 'bg-yellow-100'
    return 'bg-red-100'
  }

  if (total === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center mb-4">
          <FaceSmileIcon className="h-6 w-6 text-purple-600 mr-2" />
          <h3 className="text-lg font-semibold text-gray-900">Emotion Analytics</h3>
        </div>
        <p className="text-sm text-gray-500 text-center py-8">
          No emotion data yet. Start capturing to see analytics.
        </p>
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-xs text-blue-800">
            💡 <strong>Tip:</strong> Make sure face detection is working and students are being recognized. 
            Emotion analysis will appear here once faces are detected.
          </p>
        </div>
        
        {/* Face-API.js Emotion Recognition */}
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-xs text-green-800 mb-2">
            🎭 <strong>Face-API.js Emotion Recognition:</strong> Real-time emotion analysis
          </p>
          <div className="text-xs text-green-700">
            <div>• 7 emotion categories (happy, sad, angry, fear, surprise, disgust, neutral)</div>
            <div>• 4 engagement levels (interested, bored, confused, sleepy)</div>
            <div>• Real-time engagement scoring</div>
            <div>• Client-side processing for privacy</div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <FaceSmileIcon className="h-6 w-6 text-purple-600 mr-2" />
          <h3 className="text-lg font-semibold text-gray-900">Emotion Analytics</h3>
        </div>
        <div className="text-xs text-gray-500">
          Updated: {new Date(lastUpdateTime).toLocaleTimeString()}
        </div>
      </div>

      {/* Overall Engagement Score */}
      <div className={`mb-6 p-4 rounded-lg ${getScoreBg(engagementScore)}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-700">Overall Engagement</p>
            <p className={`text-3xl font-bold ${getScoreColor(engagementScore)}`}>
              {engagementScore}%
            </p>
          </div>
          <div className="text-4xl">
            {engagementScore >= 75 ? '🎉' : engagementScore >= 50 ? '👍' : '⚠️'}
          </div>
        </div>
        <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-500 ${
              engagementScore >= 75 ? 'bg-green-500' : 
              engagementScore >= 50 ? 'bg-yellow-500' : 
              'bg-red-500'
            }`}
            style={{ width: `${engagementScore}%` }}
          ></div>
        </div>
      </div>

      {/* Engagement Levels */}
      <div className="mb-6">
        <div className="flex items-center mb-3">
          <ChartBarIcon className="h-5 w-5 text-gray-600 mr-2" />
          <h4 className="text-sm font-semibold text-gray-700">Engagement Levels</h4>
        </div>
        <div className="space-y-3">
          {engagementData.map((item) => (
            <div key={item.level}>
              <div className="flex justify-between text-xs mb-1">
                <span className={`font-medium ${item.color} flex items-center gap-1`}>
                  <span className="text-lg">{item.emoji}</span>
                  <span className="capitalize">{item.level}</span>
                </span>
                <span className={`font-bold ${item.color}`}>
                  {item.count} ({item.percentage}%)
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2.5">
                <div 
                  className={`${item.bgColor} h-2.5 rounded-full transition-all duration-500`}
                  style={{ width: `${item.percentage}%` }}
                ></div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detailed Emotions */}
      <div>
        <h4 className="text-sm font-semibold text-gray-700 mb-3">Emotion Breakdown</h4>
        <div className="grid grid-cols-2 gap-2">
          {emotionData
            .filter(item => item.count > 0)
            .sort((a, b) => b.count - a.count)
            .map((item) => (
              <div 
                key={item.emotion}
                className="p-2 bg-gray-50 rounded-lg border border-gray-200"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1">
                    <span className="text-xl">{item.emoji}</span>
                    <span className="text-xs font-medium text-gray-700 capitalize">
                      {item.emotion}
                    </span>
                  </div>
                  <span className={`text-xs font-bold ${item.color}`}>
                    {item.percentage}%
                  </span>
                </div>
              </div>
            ))}
        </div>
      </div>

      {/* Stats Summary */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <p className="text-xs text-gray-500">Total</p>
            <p className="text-lg font-bold text-gray-900">{total}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Positive</p>
            <p className="text-lg font-bold text-green-600">
              {emotionCounts['happy'] || 0}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Negative</p>
            <p className="text-lg font-bold text-red-600">
              {(emotionCounts['sad'] || 0) + (emotionCounts['angry'] || 0) + (emotionCounts['fearful'] || 0)}
            </p>
          </div>
        </div>
        
        {/* Advanced Analytics Info */}
        <div className="mt-3 p-2 bg-gray-50 rounded text-xs">
          <p className="text-gray-600">
            <strong>Analytics:</strong> Entries: {total}, 
            Emotions: {Object.keys(emotionCounts).length}, 
            Engagement: {Object.keys(engagementCounts).length}
          </p>
          {total > 0 && (
            <>
              <p className="text-gray-600 mt-1">
                Last emotion: {entries[0]?.emotion || 'none'}, 
                Last engagement: {entries[0]?.engagement || 'none'}
              </p>
              {entries[0]?.engagement_score && (
                <p className="text-gray-600 mt-1">
                  Engagement score: {(entries[0].engagement_score * 100).toFixed(1)}%
                </p>
              )}
              {entries[0]?.engagement_score && (
                <p className="text-gray-600 mt-1">
                  🎭 Face-API.js: Active emotion detection
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}

import { useState, useEffect } from 'react'
import { useQuery } from 'react-query'
import { EmotionStatistics } from '@/types'
import { websocketService } from '@/services/websocket'

// Mock emotion data for development
const generateMockEmotionData = (): EmotionStatistics => {
  const now = Date.now()
  const variation = Math.floor(now / 5000) % 10 // Changes every 5 seconds
  
  // Simulate realistic emotion patterns during a lecture
  const baseInterested = 60 + variation * 2
  const baseBored = 25 - variation
  const baseConfused = 15 + (variation % 3)
  
  const total = baseInterested + baseBored + baseConfused
  
  return {
    interested: Math.round((baseInterested / total) * 100),
    bored: Math.round((baseBored / total) * 100),
    confused: Math.round((baseConfused / total) * 100),
    engagementScore: Math.round(baseInterested * 0.8 + (100 - baseBored) * 0.2),
    timestamp: new Date().toISOString()
  }
}

export const useEmotionAnalytics = (sessionId?: string) => {
  const [currentEmotions, setCurrentEmotions] = useState<EmotionStatistics | null>(null)
  const [emotionHistory, setEmotionHistory] = useState<EmotionStatistics[]>([])

  // Query for initial emotion data (mock for now)
  const { isLoading } = useQuery(
    ['emotions', sessionId],
    () => Promise.resolve(generateMockEmotionData()),
    {
      enabled: !!sessionId,
      refetchInterval: 5000, // Refetch every 5 seconds
      onSuccess: (data) => {
        setCurrentEmotions(data)
        setEmotionHistory(prev => {
          const newHistory = [...prev, data]
          // Keep only last 20 data points (for trend visualization)
          return newHistory.slice(-20)
        })
      },
    }
  )

  // WebSocket real-time updates
  useEffect(() => {
    if (!sessionId) return

    const handleEmotionUpdate = (emotions: EmotionStatistics) => {
      setCurrentEmotions(emotions)
      setEmotionHistory(prev => {
        const newHistory = [...prev, emotions]
        return newHistory.slice(-20)
      })
    }

    websocketService.onEmotionUpdate(handleEmotionUpdate)

    return () => {
      websocketService.offEmotionUpdate(handleEmotionUpdate)
    }
  }, [sessionId])

  // Calculate engagement trends
  const engagementTrend = emotionHistory.length >= 2 
    ? emotionHistory[emotionHistory.length - 1].engagementScore - emotionHistory[emotionHistory.length - 2].engagementScore
    : 0

  const averageEngagement = emotionHistory.length > 0
    ? Math.round(emotionHistory.reduce((sum, data) => sum + data.engagementScore, 0) / emotionHistory.length)
    : 0

  return {
    currentEmotions,
    emotionHistory,
    isLoading,
    engagementTrend,
    averageEngagement,
    hasData: !!currentEmotions
  }
}
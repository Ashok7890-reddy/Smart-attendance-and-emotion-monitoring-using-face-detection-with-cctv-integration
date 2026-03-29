/**
 * DeepFace Emotion Analysis Service
 * 
 * This service integrates with the Python DeepFace backend for advanced emotion recognition
 * and provides more accurate emotion detection than face-api.js alone.
 */

interface DeepFaceEmotionResult {
  success: boolean
  student_id: string
  emotion: string // Engagement level (interested, bored, confused, sleepy)
  raw_emotion: string // Raw emotion from DeepFace (happy, sad, angry, etc.)
  confidence: number
  engagement_score: number
  timestamp: string
  emotion_breakdown: {
    raw_emotions: Record<string, number>
    dominant_emotion: string
    engagement_distribution: Record<string, number>
  }
}

interface BatchEmotionResult {
  success: boolean
  total_processed: number
  results: DeepFaceEmotionResult[]
}

interface SessionStatistics {
  success: boolean
  session_id: string
  statistics: {
    session_id: string
    total_frames: number
    average_engagement: number
    emotion_distribution: Record<string, number>
    engagement_trend: string
    emotion_stability: number
    peak_engagement_periods: Array<{
      timestamp: string
      engagement_score: number
      emotion: string
      student_id: string
    }>
    dominant_emotion: string
    analysis_quality: {
      quality: string
      average_confidence: number
      completeness: number
      total_samples: number
    }
  }
}

class DeepFaceService {
  private baseUrl: string
  private isAvailable: boolean = false

  constructor() {
    // Use environment variable or default to localhost
    this.baseUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000'
    this.checkAvailability()
  }

  private async checkAvailability(): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/v1/deepface/health`)
      const data = await response.json()
      this.isAvailable = data.success && data.status === 'healthy'
      
      if (this.isAvailable) {
        console.log('✅ DeepFace service is available and healthy')
        console.log('🎭 Advanced emotion recognition enabled')
      } else {
        console.warn('⚠️ DeepFace service is not healthy, falling back to face-api.js')
      }
    } catch (error) {
      console.warn('⚠️ DeepFace service not available, using face-api.js fallback:', error)
      this.isAvailable = false
    }
  }

  public isServiceAvailable(): boolean {
    return this.isAvailable
  }

  /**
   * Analyze emotion from base64 image using DeepFace or fallback
   */
  public async analyzeEmotion(
    imageBase64: string, 
    studentId: string = 'unknown'
  ): Promise<DeepFaceEmotionResult | null> {
    // Try DeepFace first
    if (this.isAvailable) {
      try {
        console.log('🎭 Analyzing emotion with DeepFace...')
        
        const response = await fetch(`${this.baseUrl}/api/v1/deepface/analyze-emotion-base64`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            image_base64: imageBase64,
            student_id: studentId
          })
        })

        if (!response.ok) {
          throw new Error(`DeepFace API error: ${response.status}`)
        }

        const result: DeepFaceEmotionResult = await response.json()
        
        console.log(`🎯 DeepFace result: ${result.raw_emotion} → ${result.emotion} (${(result.confidence * 100).toFixed(1)}%)`)
        console.log(`📊 Engagement score: ${(result.engagement_score * 100).toFixed(1)}%`)
        
        return result

      } catch (error) {
        console.error('DeepFace emotion analysis failed, trying fallback:', error)
      }
    }

    // Try fallback service
    try {
      console.log('🔄 Using fallback emotion analysis...')
      
      const response = await fetch(`${this.baseUrl}/api/v1/emotion-fallback/analyze-emotion-base64`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_base64: imageBase64,
          student_id: studentId
        })
      })

      if (!response.ok) {
        throw new Error(`Fallback API error: ${response.status}`)
      }

      const result = await response.json()
      
      // Convert fallback result to DeepFace format
      const deepFaceResult: DeepFaceEmotionResult = {
        success: result.success,
        student_id: result.student_id,
        emotion: result.emotion,
        raw_emotion: result.raw_emotion,
        confidence: result.confidence,
        engagement_score: result.engagement_score,
        timestamp: result.timestamp,
        emotion_breakdown: result.emotion_breakdown
      }
      
      console.log(`🔄 Fallback result: ${result.raw_emotion} → ${result.emotion} (${(result.confidence * 100).toFixed(1)}%)`)
      
      return deepFaceResult

    } catch (error) {
      console.error('Fallback emotion analysis also failed:', error)
      return null
    }
  }

  /**
   * Analyze emotions for multiple images in batch
   */
  public async analyzeBatchEmotions(
    imagesBase64: string[], 
    studentIds?: string[]
  ): Promise<BatchEmotionResult | null> {
    if (!this.isAvailable) {
      console.warn('DeepFace service not available')
      return null
    }

    try {
      console.log(`🎭 Analyzing ${imagesBase64.length} images with DeepFace batch processing...`)
      
      const response = await fetch(`${this.baseUrl}/api/v1/deepface/analyze-batch-emotions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          images_base64: imagesBase64,
          student_ids: studentIds
        })
      })

      if (!response.ok) {
        throw new Error(`DeepFace batch API error: ${response.status}`)
      }

      const result: BatchEmotionResult = await response.json()
      
      console.log(`🎯 DeepFace batch result: ${result.total_processed} images processed`)
      
      return result

    } catch (error) {
      console.error('DeepFace batch emotion analysis failed:', error)
      return null
    }
  }

  /**
   * Update session with new emotion data
   */
  public async updateSession(
    sessionId: string,
    imageBase64: string,
    studentId: string = 'unknown'
  ): Promise<any> {
    if (!this.isAvailable) {
      return null
    }

    try {
      // Convert base64 to blob for FormData
      const byteCharacters = atob(imageBase64)
      const byteNumbers = new Array(byteCharacters.length)
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i)
      }
      const byteArray = new Uint8Array(byteNumbers)
      const blob = new Blob([byteArray], { type: 'image/jpeg' })

      const formData = new FormData()
      formData.append('image', blob, 'emotion_image.jpg')
      formData.append('student_id', studentId)

      const response = await fetch(`${this.baseUrl}/api/v1/deepface/update-session/${sessionId}`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error(`DeepFace session update error: ${response.status}`)
      }

      const result = await response.json()
      console.log(`📊 Session ${sessionId} updated with DeepFace emotion data`)
      
      return result

    } catch (error) {
      console.error('DeepFace session update failed:', error)
      return null
    }
  }

  /**
   * Get comprehensive session statistics
   */
  public async getSessionStatistics(sessionId: string): Promise<SessionStatistics | null> {
    if (!this.isAvailable) {
      return null
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/deepface/session-statistics/${sessionId}`)

      if (!response.ok) {
        if (response.status === 404) {
          console.warn(`Session ${sessionId} not found in DeepFace service`)
          return null
        }
        throw new Error(`DeepFace statistics error: ${response.status}`)
      }

      const result: SessionStatistics = await response.json()
      console.log(`📊 Retrieved DeepFace statistics for session ${sessionId}`)
      
      return result

    } catch (error) {
      console.error('DeepFace session statistics failed:', error)
      return null
    }
  }

  /**
   * Get real-time engagement metrics
   */
  public async getRealTimeMetrics(sessionId: string): Promise<any> {
    if (!this.isAvailable) {
      return null
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/deepface/real-time-metrics/${sessionId}`)

      if (!response.ok) {
        if (response.status === 404) {
          return null
        }
        throw new Error(`DeepFace metrics error: ${response.status}`)
      }

      const result = await response.json()
      return result

    } catch (error) {
      console.error('DeepFace real-time metrics failed:', error)
      return null
    }
  }

  /**
   * Get list of active sessions
   */
  public async getActiveSessions(): Promise<string[]> {
    if (!this.isAvailable) {
      return []
    }

    try {
      const response = await fetch(`${this.baseUrl}/api/v1/deepface/active-sessions`)

      if (!response.ok) {
        throw new Error(`DeepFace active sessions error: ${response.status}`)
      }

      const result = await response.json()
      return result.active_sessions || []

    } catch (error) {
      console.error('DeepFace active sessions failed:', error)
      return []
    }
  }

  /**
   * Map DeepFace emotions to engagement levels
   */
  public mapEmotionToEngagement(rawEmotion: string): string {
    const emotionMap: Record<string, string> = {
      'happy': 'interested',
      'surprise': 'interested',
      'neutral': 'bored',
      'sad': 'sleepy',
      'angry': 'confused',
      'disgust': 'bored',
      'fear': 'confused'
    }
    
    return emotionMap[rawEmotion] || 'bored'
  }

  /**
   * Get emotion emoji for display
   */
  public getEmotionEmoji(emotion: string): string {
    const emojiMap: Record<string, string> = {
      'happy': '😊',
      'sad': '😢',
      'angry': '😠',
      'fear': '😨',
      'surprise': '😲',
      'disgust': '🤢',
      'neutral': '😐',
      // Engagement levels
      'interested': '😊',
      'bored': '😐',
      'confused': '😕',
      'sleepy': '😴'
    }
    
    return emojiMap[emotion] || '😐'
  }

  /**
   * Get engagement color for UI
   */
  public getEngagementColor(engagement: string): string {
    const colorMap: Record<string, string> = {
      'interested': 'text-green-600',
      'bored': 'text-yellow-600',
      'confused': 'text-orange-600',
      'sleepy': 'text-red-600'
    }
    
    return colorMap[engagement] || 'text-gray-600'
  }

  /**
   * Get engagement background color for UI
   */
  public getEngagementBgColor(engagement: string): string {
    const bgColorMap: Record<string, string> = {
      'interested': 'bg-green-100',
      'bored': 'bg-yellow-100',
      'confused': 'bg-orange-100',
      'sleepy': 'bg-red-100'
    }
    
    return bgColorMap[engagement] || 'bg-gray-100'
  }

  /**
   * Calculate overall engagement score from multiple results
   */
  public calculateOverallEngagement(results: DeepFaceEmotionResult[]): number {
    if (results.length === 0) return 0

    const totalScore = results.reduce((sum, result) => sum + result.engagement_score, 0)
    return totalScore / results.length
  }

  /**
   * Get engagement level from score
   */
  public getEngagementLevel(score: number): string {
    if (score >= 0.75) return 'High'
    if (score >= 0.50) return 'Medium'
    if (score >= 0.25) return 'Low'
    return 'Very Low'
  }

  /**
   * Format emotion breakdown for display
   */
  public formatEmotionBreakdown(breakdown: any): string {
    if (!breakdown?.raw_emotions) return 'No data'

    const emotions = Object.entries(breakdown.raw_emotions)
      .sort(([,a], [,b]) => (b as number) - (a as number))
      .slice(0, 3)
      .map(([emotion, percentage]) => `${emotion}: ${(percentage as number).toFixed(1)}%`)
      .join(', ')

    return emotions
  }
}

// Create and export singleton instance
export const deepFaceService = new DeepFaceService()
export type { DeepFaceEmotionResult, BatchEmotionResult, SessionStatistics }
import { io, Socket } from 'socket.io-client'
import { AttendanceSession, EmotionStatistics, SystemAlert } from '@/types'

class WebSocketService {
  private socket: Socket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  connect() {
    if (this.socket?.connected) return

    this.socket = io(import.meta.env.VITE_WS_URL || 'ws://localhost:8000', {
      transports: ['websocket'],
      autoConnect: true,
    })

    this.socket.on('connect', () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
    })

    this.socket.on('disconnect', () => {
      console.log('WebSocket disconnected')
      this.handleReconnect()
    })

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      this.handleReconnect()
    })
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      setTimeout(() => {
        console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
        this.connect()
      }, 2000 * this.reconnectAttempts)
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
  }

  // Attendance updates
  onAttendanceUpdate(callback: (session: AttendanceSession) => void) {
    this.socket?.on('attendance_update', callback)
  }

  offAttendanceUpdate(callback: (session: AttendanceSession) => void) {
    this.socket?.off('attendance_update', callback)
  }

  // Emotion statistics updates
  onEmotionUpdate(callback: (emotions: EmotionStatistics) => void) {
    this.socket?.on('emotion_update', callback)
  }

  offEmotionUpdate(callback: (emotions: EmotionStatistics) => void) {
    this.socket?.off('emotion_update', callback)
  }

  // System alerts
  onSystemAlert(callback: (alert: SystemAlert) => void) {
    this.socket?.on('system_alert', callback)
  }

  offSystemAlert(callback: (alert: SystemAlert) => void) {
    this.socket?.off('system_alert', callback)
  }

  // Join/leave session rooms
  joinSession(sessionId: string) {
    this.socket?.emit('join_session', sessionId)
  }

  leaveSession(sessionId: string) {
    this.socket?.emit('leave_session', sessionId)
  }

  isConnected(): boolean {
    return this.socket?.connected || false
  }
}

export const websocketService = new WebSocketService()
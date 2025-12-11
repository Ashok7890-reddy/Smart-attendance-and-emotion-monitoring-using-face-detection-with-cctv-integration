import { websocketService } from '../websocket'
import { io } from 'socket.io-client'

// Mock socket.io-client
vi.mock('socket.io-client')

const mockIo = vi.mocked(io)
const mockSocket = {
  connected: false,
  on: vi.fn(),
  off: vi.fn(),
  emit: vi.fn(),
  disconnect: vi.fn(),
}

describe('WebSocketService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockIo.mockReturnValue(mockSocket)
  })

  it('creates socket connection on connect', () => {
    websocketService.connect()

    expect(mockIo).toHaveBeenCalledWith('ws://localhost:8000', {
      transports: ['websocket'],
      autoConnect: true,
    })
  })

  it('sets up event listeners on connect', () => {
    websocketService.connect()

    expect(mockSocket.on).toHaveBeenCalledWith('connect', expect.any(Function))
    expect(mockSocket.on).toHaveBeenCalledWith('disconnect', expect.any(Function))
    expect(mockSocket.on).toHaveBeenCalledWith('connect_error', expect.any(Function))
  })

  it('does not create new connection if already connected', () => {
    mockSocket.connected = true
    websocketService.connect()
    websocketService.connect()

    expect(mockIo).toHaveBeenCalledTimes(1)
  })

  it('joins session room', () => {
    websocketService.connect()
    websocketService.joinSession('session-001')

    expect(mockSocket.emit).toHaveBeenCalledWith('join_session', 'session-001')
  })

  it('leaves session room', () => {
    websocketService.connect()
    websocketService.leaveSession('session-001')

    expect(mockSocket.emit).toHaveBeenCalledWith('leave_session', 'session-001')
  })

  it('registers attendance update listener', () => {
    const callback = vi.fn()
    websocketService.connect()
    websocketService.onAttendanceUpdate(callback)

    expect(mockSocket.on).toHaveBeenCalledWith('attendance_update', callback)
  })

  it('unregisters attendance update listener', () => {
    const callback = vi.fn()
    websocketService.connect()
    websocketService.offAttendanceUpdate(callback)

    expect(mockSocket.off).toHaveBeenCalledWith('attendance_update', callback)
  })

  it('registers emotion update listener', () => {
    const callback = vi.fn()
    websocketService.connect()
    websocketService.onEmotionUpdate(callback)

    expect(mockSocket.on).toHaveBeenCalledWith('emotion_update', callback)
  })

  it('registers system alert listener', () => {
    const callback = vi.fn()
    websocketService.connect()
    websocketService.onSystemAlert(callback)

    expect(mockSocket.on).toHaveBeenCalledWith('system_alert', callback)
  })

  it('disconnects socket', () => {
    websocketService.connect()
    websocketService.disconnect()

    expect(mockSocket.disconnect).toHaveBeenCalled()
  })

  it('returns connection status', () => {
    websocketService.connect()
    mockSocket.connected = true

    expect(websocketService.isConnected()).toBe(true)

    mockSocket.connected = false
    expect(websocketService.isConnected()).toBe(false)
  })
})
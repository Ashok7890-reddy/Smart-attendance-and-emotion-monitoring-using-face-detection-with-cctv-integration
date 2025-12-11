import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from 'react-query'
import { vi } from 'vitest'
import { useAttendanceSession } from '../useAttendanceSession'
import { attendanceAPI } from '@/services/api'
import { websocketService } from '@/services/websocket'

// Mock the API and WebSocket service
vi.mock('@/services/api')
vi.mock('@/services/websocket')

const mockAttendanceAPI = vi.mocked(attendanceAPI)
const mockWebsocketService = vi.mocked(websocketService)

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('useAttendanceSession', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockWebsocketService.connect = vi.fn()
    mockWebsocketService.joinSession = vi.fn()
    mockWebsocketService.leaveSession = vi.fn()
    mockWebsocketService.onAttendanceUpdate = vi.fn()
    mockWebsocketService.offAttendanceUpdate = vi.fn()
  })

  it('fetches current session on mount', async () => {
    const mockSession = {
      id: 'session-001',
      classId: 'CS101',
      facultyId: 'faculty-001',
      startTime: '2024-01-15T09:00:00Z',
      totalRegistered: 50,
      totalDetected: 42,
      attendancePercentage: 84,
      status: 'active'
    }

    mockAttendanceAPI.getCurrentSession.mockResolvedValue(mockSession)
    mockAttendanceAPI.getSessionStudents.mockResolvedValue([])

    const { result } = renderHook(() => useAttendanceSession(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.currentSession).toEqual(mockSession)
    })

    expect(mockAttendanceAPI.getCurrentSession).toHaveBeenCalled()
  })

  it('calculates attendance percentage correctly', async () => {
    const mockStudents = [
      { id: '1', name: 'Alice', studentId: 'CS001', type: 'day_scholar', isPresent: true },
      { id: '2', name: 'Bob', studentId: 'CS002', type: 'hostel_student', isPresent: true },
      { id: '3', name: 'Carol', studentId: 'CS003', type: 'day_scholar', isPresent: false },
      { id: '4', name: 'David', studentId: 'CS004', type: 'hostel_student', isPresent: false },
    ]

    mockAttendanceAPI.getCurrentSession.mockResolvedValue({
      id: 'session-001',
      classId: 'CS101',
      status: 'active'
    })
    mockAttendanceAPI.getSessionStudents.mockResolvedValue(mockStudents)

    const { result } = renderHook(() => useAttendanceSession(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(result.current.attendancePercentage).toBe(50) // 2 out of 4 students present
      expect(result.current.presentStudents).toHaveLength(2)
      expect(result.current.absentStudents).toHaveLength(2)
    })
  })

  it('connects to WebSocket on mount', () => {
    renderHook(() => useAttendanceSession(), {
      wrapper: createWrapper(),
    })

    expect(mockWebsocketService.connect).toHaveBeenCalled()
  })

  it('joins session room when session is available', async () => {
    const mockSession = {
      id: 'session-001',
      classId: 'CS101',
      status: 'active'
    }

    mockAttendanceAPI.getCurrentSession.mockResolvedValue(mockSession)
    mockAttendanceAPI.getSessionStudents.mockResolvedValue([])

    renderHook(() => useAttendanceSession(), {
      wrapper: createWrapper(),
    })

    await waitFor(() => {
      expect(mockWebsocketService.joinSession).toHaveBeenCalledWith('session-001')
    })
  })

  it('returns correct loading state', () => {
    mockAttendanceAPI.getCurrentSession.mockImplementation(() => new Promise(() => {}))

    const { result } = renderHook(() => useAttendanceSession(), {
      wrapper: createWrapper(),
    })

    expect(result.current.isLoading).toBe(true)
  })
})
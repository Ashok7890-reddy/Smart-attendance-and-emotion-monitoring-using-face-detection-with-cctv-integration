import { render, screen, fireEvent } from '@testing-library/react'
import { SessionControls } from '../Dashboard/SessionControls'
import { AttendanceSession } from '@/types'

const mockSession: AttendanceSession = {
  id: 'session-001',
  classId: 'CS101',
  facultyId: 'faculty-001',
  startTime: '2024-01-15T09:00:00Z',
  totalRegistered: 50,
  totalDetected: 42,
  attendancePercentage: 84,
  status: 'active'
}

describe('SessionControls', () => {
  const mockStartSession = vi.fn()
  const mockEndSession = vi.fn()

  beforeEach(() => {
    mockStartSession.mockClear()
    mockEndSession.mockClear()
  })

  it('shows start session interface when no active session', () => {
    render(
      <SessionControls
        currentSession={null}
        onStartSession={mockStartSession}
        onEndSession={mockEndSession}
        isStarting={false}
        isEnding={false}
      />
    )
    
    expect(screen.getByText('Start Attendance Session')).toBeInTheDocument()
    expect(screen.getByText('Start Session')).toBeInTheDocument()
  })

  it('shows active session interface when session is running', () => {
    render(
      <SessionControls
        currentSession={mockSession}
        onStartSession={mockStartSession}
        onEndSession={mockEndSession}
        isStarting={false}
        isEnding={false}
      />
    )
    
    expect(screen.getByText('Session Active')).toBeInTheDocument()
    expect(screen.getByText('End Session')).toBeInTheDocument()
    expect(screen.getByText('Class: CS101')).toBeInTheDocument()
  })

  it('calls onStartSession when start button is clicked', () => {
    render(
      <SessionControls
        currentSession={null}
        onStartSession={mockStartSession}
        onEndSession={mockEndSession}
        isStarting={false}
        isEnding={false}
      />
    )
    
    const classInput = screen.getByDisplayValue('CS101')
    fireEvent.change(classInput, { target: { value: 'CS102' } })
    
    const startButton = screen.getByText('Start Session')
    fireEvent.click(startButton)
    
    expect(mockStartSession).toHaveBeenCalledWith('CS102')
  })

  it('shows confirmation dialog when end session is clicked', () => {
    render(
      <SessionControls
        currentSession={mockSession}
        onStartSession={mockStartSession}
        onEndSession={mockEndSession}
        isStarting={false}
        isEnding={false}
      />
    )
    
    const endButton = screen.getByText('End Session')
    fireEvent.click(endButton)
    
    expect(screen.getByText('End session?')).toBeInTheDocument()
    expect(screen.getByText('Confirm')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
  })

  it('calls onEndSession when confirmed', () => {
    render(
      <SessionControls
        currentSession={mockSession}
        onStartSession={mockStartSession}
        onEndSession={mockEndSession}
        isStarting={false}
        isEnding={false}
      />
    )
    
    const endButton = screen.getByText('End Session')
    fireEvent.click(endButton)
    
    const confirmButton = screen.getByText('Confirm')
    fireEvent.click(confirmButton)
    
    expect(mockEndSession).toHaveBeenCalledWith('session-001')
  })

  it('shows loading state when starting session', () => {
    render(
      <SessionControls
        currentSession={null}
        onStartSession={mockStartSession}
        onEndSession={mockEndSession}
        isStarting={true}
        isEnding={false}
      />
    )
    
    expect(screen.getByText('Starting...')).toBeInTheDocument()
  })

  it('shows loading state when ending session', () => {
    render(
      <SessionControls
        currentSession={mockSession}
        onStartSession={mockStartSession}
        onEndSession={mockEndSession}
        isStarting={false}
        isEnding={true}
      />
    )
    
    const endButton = screen.getByText('End Session')
    fireEvent.click(endButton)
    
    const confirmButton = screen.getByText('Ending...')
    expect(confirmButton).toBeInTheDocument()
  })
})
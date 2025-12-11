import { render, screen } from '@testing-library/react'
import { AttendanceStats } from '../Dashboard/AttendanceStats'

describe('AttendanceStats', () => {
  const defaultProps = {
    totalStudents: 50,
    presentStudents: 42,
    absentStudents: 8,
    attendancePercentage: 84,
  }

  it('renders attendance statistics correctly', () => {
    render(<AttendanceStats {...defaultProps} />)
    
    expect(screen.getByText('50')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('8')).toBeInTheDocument()
    expect(screen.getByText('84%')).toBeInTheDocument()
  })

  it('shows live indicator when session is active', () => {
    render(<AttendanceStats {...defaultProps} isLive={true} />)
    
    expect(screen.getByText('Live')).toBeInTheDocument()
  })

  it('does not show live indicator when session is inactive', () => {
    render(<AttendanceStats {...defaultProps} isLive={false} />)
    
    expect(screen.queryByText('Live')).not.toBeInTheDocument()
  })

  it('applies correct color coding for high attendance', () => {
    render(<AttendanceStats {...defaultProps} attendancePercentage={90} />)
    
    const attendanceCard = screen.getByText('90%').closest('.card')
    expect(attendanceCard).toHaveClass('border-green-400')
  })

  it('applies correct color coding for medium attendance', () => {
    render(<AttendanceStats {...defaultProps} attendancePercentage={70} />)
    
    const attendanceCard = screen.getByText('70%').closest('.card')
    expect(attendanceCard).toHaveClass('border-yellow-400')
  })

  it('applies correct color coding for low attendance', () => {
    render(<AttendanceStats {...defaultProps} attendancePercentage={50} />)
    
    const attendanceCard = screen.getByText('50%').closest('.card')
    expect(attendanceCard).toHaveClass('border-red-400')
  })
})
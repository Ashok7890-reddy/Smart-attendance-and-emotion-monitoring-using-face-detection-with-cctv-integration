import { render, screen, fireEvent } from '@testing-library/react'
import { StudentList } from '../Dashboard/StudentList'
import { Student } from '@/types'

const mockStudents: Student[] = [
  {
    id: '1',
    name: 'Alice Johnson',
    studentId: 'CS2021001',
    type: 'day_scholar',
    isPresent: true,
    gateEntry: '2024-01-15T09:15:00Z',
    classroomEntry: '2024-01-15T09:30:00Z'
  },
  {
    id: '2',
    name: 'Bob Smith',
    studentId: 'CS2021002',
    type: 'hostel_student',
    isPresent: false,
  },
  {
    id: '3',
    name: 'Carol Davis',
    studentId: 'CS2021003',
    type: 'day_scholar',
    isPresent: true,
    gateEntry: '2024-01-15T09:10:00Z',
    classroomEntry: '2024-01-15T09:25:00Z'
  }
]

describe('StudentList', () => {
  it('renders student list correctly', () => {
    render(<StudentList students={mockStudents} />)
    
    expect(screen.getByText('Alice Johnson')).toBeInTheDocument()
    expect(screen.getByText('Bob Smith')).toBeInTheDocument()
    expect(screen.getByText('Carol Davis')).toBeInTheDocument()
  })

  it('shows correct present and absent counts', () => {
    render(<StudentList students={mockStudents} />)
    
    expect(screen.getByText('2 Present')).toBeInTheDocument()
    expect(screen.getByText('1 Absent')).toBeInTheDocument()
  })

  it('filters students by search term', () => {
    render(<StudentList students={mockStudents} />)
    
    const searchInput = screen.getByPlaceholderText('Search students...')
    fireEvent.change(searchInput, { target: { value: 'Alice' } })
    
    expect(screen.getByText('Alice Johnson')).toBeInTheDocument()
    expect(screen.queryByText('Bob Smith')).not.toBeInTheDocument()
    expect(screen.queryByText('Carol Davis')).not.toBeInTheDocument()
  })

  it('filters students by presence status', () => {
    render(<StudentList students={mockStudents} />)
    
    const presentButton = screen.getByText('Present')
    fireEvent.click(presentButton)
    
    expect(screen.getByText('Alice Johnson')).toBeInTheDocument()
    expect(screen.getByText('Carol Davis')).toBeInTheDocument()
    expect(screen.queryByText('Bob Smith')).not.toBeInTheDocument()
  })

  it('shows loading state', () => {
    render(<StudentList students={[]} isLoading={true} />)
    
    expect(screen.getByTestId('loading-skeleton') || document.querySelector('.animate-pulse')).toBeInTheDocument()
  })

  it('shows empty state when no students found', () => {
    render(<StudentList students={[]} />)
    
    expect(screen.getByText('No students found')).toBeInTheDocument()
  })

  it('displays student status correctly', () => {
    render(<StudentList students={mockStudents} />)
    
    const presentBadges = screen.getAllByText('Present')
    const absentBadges = screen.getAllByText('Absent')
    
    expect(presentBadges).toHaveLength(3) // 2 students + 1 filter button
    expect(absentBadges).toHaveLength(2) // 1 student + 1 filter button
  })
})
import { render, screen, fireEvent } from '@testing-library/react'
import { DateRangePicker } from '../Reports/DateRangePicker'

describe('DateRangePicker', () => {
  const mockOnStartDateChange = vi.fn()
  const mockOnEndDateChange = vi.fn()

  const defaultProps = {
    startDate: '2024-01-01',
    endDate: '2024-01-07',
    onStartDateChange: mockOnStartDateChange,
    onEndDateChange: mockOnEndDateChange,
  }

  beforeEach(() => {
    mockOnStartDateChange.mockClear()
    mockOnEndDateChange.mockClear()
  })

  it('renders date inputs with correct values', () => {
    render(<DateRangePicker {...defaultProps} />)
    
    const startDateInput = screen.getByLabelText('Start Date') as HTMLInputElement
    const endDateInput = screen.getByLabelText('End Date') as HTMLInputElement
    
    expect(startDateInput.value).toBe('2024-01-01')
    expect(endDateInput.value).toBe('2024-01-07')
  })

  it('calls onStartDateChange when start date is changed', () => {
    render(<DateRangePicker {...defaultProps} />)
    
    const startDateInput = screen.getByLabelText('Start Date')
    fireEvent.change(startDateInput, { target: { value: '2024-01-02' } })
    
    expect(mockOnStartDateChange).toHaveBeenCalledWith('2024-01-02')
  })

  it('calls onEndDateChange when end date is changed', () => {
    render(<DateRangePicker {...defaultProps} />)
    
    const endDateInput = screen.getByLabelText('End Date')
    fireEvent.change(endDateInput, { target: { value: '2024-01-08' } })
    
    expect(mockOnEndDateChange).toHaveBeenCalledWith('2024-01-08')
  })

  it('renders quick select buttons', () => {
    render(<DateRangePicker {...defaultProps} />)
    
    expect(screen.getByText('Today')).toBeInTheDocument()
    expect(screen.getByText('Last 7 days')).toBeInTheDocument()
    expect(screen.getByText('Last 30 days')).toBeInTheDocument()
    expect(screen.getByText('Last 90 days')).toBeInTheDocument()
  })

  it('calls date change handlers when quick select is used', () => {
    render(<DateRangePicker {...defaultProps} />)
    
    const last7DaysButton = screen.getByText('Last 7 days')
    fireEvent.click(last7DaysButton)
    
    expect(mockOnStartDateChange).toHaveBeenCalled()
    expect(mockOnEndDateChange).toHaveBeenCalled()
  })

  it('sets today as end date when Today is clicked', () => {
    render(<DateRangePicker {...defaultProps} />)
    
    const todayButton = screen.getByText('Today')
    fireEvent.click(todayButton)
    
    const today = new Date().toISOString().split('T')[0]
    expect(mockOnEndDateChange).toHaveBeenCalledWith(today)
  })
})
import { render, screen } from '@testing-library/react'
import { EmotionMetrics } from '../Analytics/EmotionMetrics'
import { EmotionStatistics } from '@/types'

const mockEmotions: EmotionStatistics = {
  interested: 65,
  bored: 20,
  confused: 15,
  engagementScore: 72,
  timestamp: '2024-01-15T09:35:00Z'
}

describe('EmotionMetrics', () => {
  const defaultProps = {
    currentEmotions: mockEmotions,
    averageEngagement: 68,
    engagementTrend: 5,
  }

  it('renders emotion percentages correctly', () => {
    render(<EmotionMetrics {...defaultProps} />)
    
    expect(screen.getByText('65%')).toBeInTheDocument()
    expect(screen.getByText('20%')).toBeInTheDocument()
    expect(screen.getByText('15%')).toBeInTheDocument()
  })

  it('displays current and average engagement scores', () => {
    render(<EmotionMetrics {...defaultProps} />)
    
    expect(screen.getByText('72%')).toBeInTheDocument()
    expect(screen.getByText('68%')).toBeInTheDocument()
  })

  it('shows positive trend indicator', () => {
    render(<EmotionMetrics {...defaultProps} engagementTrend={5} />)
    
    expect(screen.getByText('+5.0%')).toBeInTheDocument()
  })

  it('shows negative trend indicator', () => {
    render(<EmotionMetrics {...defaultProps} engagementTrend={-3} />)
    
    expect(screen.getByText('-3.0%')).toBeInTheDocument()
  })

  it('shows no change for small trends', () => {
    render(<EmotionMetrics {...defaultProps} engagementTrend={1} />)
    
    expect(screen.getByText('No change')).toBeInTheDocument()
  })

  it('displays correct engagement level for high score', () => {
    const highEngagementEmotions = { ...mockEmotions, engagementScore: 85 }
    render(<EmotionMetrics {...defaultProps} currentEmotions={highEngagementEmotions} />)
    
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('displays correct engagement level for medium score', () => {
    const mediumEngagementEmotions = { ...mockEmotions, engagementScore: 65 }
    render(<EmotionMetrics {...defaultProps} currentEmotions={mediumEngagementEmotions} />)
    
    expect(screen.getByText('Medium')).toBeInTheDocument()
  })

  it('displays correct engagement level for low score', () => {
    const lowEngagementEmotions = { ...mockEmotions, engagementScore: 45 }
    render(<EmotionMetrics {...defaultProps} currentEmotions={lowEngagementEmotions} />)
    
    expect(screen.getByText('Low')).toBeInTheDocument()
  })

  it('renders engagement progress bar with correct width', () => {
    render(<EmotionMetrics {...defaultProps} />)
    
    const progressBar = document.querySelector('[style*="width: 72%"]')
    expect(progressBar).toBeInTheDocument()
  })
})
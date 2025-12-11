import React from 'react'
import { Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  ChartOptions
} from 'chart.js'
import { EmotionStatistics } from '@/types'

ChartJS.register(ArcElement, Tooltip, Legend)

interface EmotionPieChartProps {
  emotions: EmotionStatistics
  className?: string
}

export const EmotionPieChart: React.FC<EmotionPieChartProps> = ({ 
  emotions, 
  className = '' 
}) => {
  const data = {
    labels: ['Interested', 'Bored', 'Confused'],
    datasets: [
      {
        data: [emotions.interested, emotions.bored, emotions.confused],
        backgroundColor: [
          '#10B981', // Green for interested
          '#F59E0B', // Yellow for bored  
          '#EF4444', // Red for confused
        ],
        borderColor: [
          '#059669',
          '#D97706',
          '#DC2626',
        ],
        borderWidth: 2,
        hoverBackgroundColor: [
          '#34D399',
          '#FBBF24',
          '#F87171',
        ],
      },
    ],
  }

  const options: ChartOptions<'doughnut'> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom',
        labels: {
          padding: 20,
          usePointStyle: true,
          font: {
            size: 12,
          },
        },
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const label = context.label || ''
            const value = context.parsed
            return `${label}: ${value}%`
          },
        },
      },
    },
    cutout: '60%',
  }

  return (
    <div className={`relative ${className}`}>
      <Doughnut data={data} options={options} />
      
      {/* Center text showing engagement score */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">
            {emotions.engagementScore}%
          </div>
          <div className="text-sm text-gray-600">
            Engagement
          </div>
        </div>
      </div>
    </div>
  )
}
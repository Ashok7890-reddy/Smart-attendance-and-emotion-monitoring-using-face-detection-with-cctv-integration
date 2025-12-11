import React from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions
} from 'chart.js'
import { EmotionStatistics } from '@/types'


ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

interface EngagementTrendChartProps {
  emotionHistory: EmotionStatistics[]
  className?: string
}

export const EngagementTrendChart: React.FC<EngagementTrendChartProps> = ({ 
  emotionHistory, 
  className = '' 
}) => {
  const labels = emotionHistory.map((_, index) => {
    const minutesAgo = emotionHistory.length - index - 1
    return minutesAgo === 0 ? 'Now' : `${minutesAgo}m ago`
  })

  const data = {
    labels,
    datasets: [
      {
        label: 'Interested',
        data: emotionHistory.map(e => e.interested),
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        tension: 0.4,
        fill: false,
      },
      {
        label: 'Bored',
        data: emotionHistory.map(e => e.bored),
        borderColor: '#F59E0B',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        tension: 0.4,
        fill: false,
      },
      {
        label: 'Confused',
        data: emotionHistory.map(e => e.confused),
        borderColor: '#EF4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.4,
        fill: false,
      },
      {
        label: 'Engagement Score',
        data: emotionHistory.map(e => e.engagementScore),
        borderColor: '#3B82F6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        tension: 0.4,
        fill: true,
        borderWidth: 3,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  }

  const options: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
        },
      },
      tooltip: {
        callbacks: {
          label: (context) => {
            const label = context.dataset.label || ''
            const value = context.parsed.y
            return `${label}: ${value}%`
          },
        },
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time',
        },
        grid: {
          display: false,
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Percentage (%)',
        },
        min: 0,
        max: 100,
        grid: {
          color: 'rgba(0, 0, 0, 0.1)',
        },
      },
    },
  }

  if (emotionHistory.length === 0) {
    return (
      <div className={`flex items-center justify-center h-64 bg-gray-50 rounded-lg ${className}`}>
        <div className="text-center text-gray-500">
          <div className="text-lg font-medium mb-2">No data available</div>
          <div className="text-sm">Emotion trends will appear here during an active session</div>
        </div>
      </div>
    )
  }

  return (
    <div className={`relative ${className}`}>
      <Line data={data} options={options} />
    </div>
  )
}
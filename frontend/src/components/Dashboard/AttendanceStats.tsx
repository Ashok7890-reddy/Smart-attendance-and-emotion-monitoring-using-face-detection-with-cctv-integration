import React from 'react'
import { 
  UserGroupIcon, 
  CheckCircleIcon, 
  XCircleIcon,
  ClockIcon 
} from '@heroicons/react/24/outline'

interface AttendanceStatsProps {
  totalStudents: number
  presentStudents: number
  absentStudents: number
  attendancePercentage: number
  isLive?: boolean
}

export const AttendanceStats: React.FC<AttendanceStatsProps> = ({
  totalStudents,
  presentStudents,
  absentStudents,
  attendancePercentage,
  isLive = false
}) => {
  const stats = [
    {
      name: 'Total Students',
      value: totalStudents,
      icon: UserGroupIcon,
      color: 'bg-blue-100 text-blue-600',
      bgColor: 'bg-blue-50'
    },
    {
      name: 'Present',
      value: presentStudents,
      icon: CheckCircleIcon,
      color: 'bg-green-100 text-green-600',
      bgColor: 'bg-green-50'
    },
    {
      name: 'Absent',
      value: absentStudents,
      icon: XCircleIcon,
      color: 'bg-red-100 text-red-600',
      bgColor: 'bg-red-50'
    },
    {
      name: 'Attendance Rate',
      value: `${attendancePercentage}%`,
      icon: ClockIcon,
      color: attendancePercentage >= 80 ? 'bg-green-100 text-green-600' : 
             attendancePercentage >= 60 ? 'bg-yellow-100 text-yellow-600' : 
             'bg-red-100 text-red-600',
      bgColor: attendancePercentage >= 80 ? 'bg-green-50' : 
               attendancePercentage >= 60 ? 'bg-yellow-50' : 
               'bg-red-50'
    }
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      {stats.map((stat) => (
        <div key={stat.name} className={`card ${stat.bgColor} border-l-4 ${
          stat.name === 'Attendance Rate' && attendancePercentage >= 80 ? 'border-green-400' :
          stat.name === 'Attendance Rate' && attendancePercentage >= 60 ? 'border-yellow-400' :
          stat.name === 'Attendance Rate' ? 'border-red-400' :
          stat.name === 'Present' ? 'border-green-400' :
          stat.name === 'Absent' ? 'border-red-400' :
          'border-blue-400'
        }`}>
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center">
                <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                {isLive && (
                  <div className="ml-2 flex items-center">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                    <span className="ml-1 text-xs text-green-600">Live</span>
                  </div>
                )}
              </div>
              <p className="text-2xl font-bold text-gray-900 mt-1">{stat.value}</p>
            </div>
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${stat.color}`}>
              <stat.icon className="h-6 w-6" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
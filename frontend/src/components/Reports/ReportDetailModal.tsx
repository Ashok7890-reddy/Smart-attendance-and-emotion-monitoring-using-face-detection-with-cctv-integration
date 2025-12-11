import React from 'react'
import { 
  XMarkIcon,
  UserGroupIcon,
  CheckCircleIcon,
  XCircleIcon,
  ChartBarIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { AttendanceReport } from '@/types'
import { format } from 'date-fns'

interface ReportDetailModalProps {
  report: AttendanceReport | null
  isOpen: boolean
  onClose: () => void
  onExport: (format: 'pdf' | 'csv' | 'excel') => void
}

export const ReportDetailModal: React.FC<ReportDetailModalProps> = ({
  report,
  isOpen,
  onClose,
  onExport
}) => {
  if (!isOpen || !report) return null

  const presentStudents = report.students.filter(s => s.isPresent)
  const absentStudents = report.students.filter(s => !s.isPresent)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              {report.className} - Attendance Report
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {format(new Date(report.date), 'MMMM dd, yyyy')} • {report.startTime} - {report.endTime}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors duration-200"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
          {/* Summary Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center">
                <UserGroupIcon className="h-8 w-8 text-blue-600" />
                <div className="ml-3">
                  <p className="text-sm font-medium text-blue-600">Total Students</p>
                  <p className="text-2xl font-bold text-blue-900">{report.totalStudents}</p>
                </div>
              </div>
            </div>

            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-center">
                <CheckCircleIcon className="h-8 w-8 text-green-600" />
                <div className="ml-3">
                  <p className="text-sm font-medium text-green-600">Present</p>
                  <p className="text-2xl font-bold text-green-900">{report.presentStudents}</p>
                </div>
              </div>
            </div>

            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-center">
                <XCircleIcon className="h-8 w-8 text-red-600" />
                <div className="ml-3">
                  <p className="text-sm font-medium text-red-600">Absent</p>
                  <p className="text-2xl font-bold text-red-900">{absentStudents.length}</p>
                </div>
              </div>
            </div>

            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
              <div className="flex items-center">
                <ChartBarIcon className="h-8 w-8 text-purple-600" />
                <div className="ml-3">
                  <p className="text-sm font-medium text-purple-600">Engagement</p>
                  <p className="text-2xl font-bold text-purple-900">{report.emotionStatistics.engagementScore}%</p>
                </div>
              </div>
            </div>
          </div>

          {/* Emotion Statistics */}
          <div className="mb-8">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Emotion Analysis</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="text-center">
                  <p className="text-sm font-medium text-green-600">Interested</p>
                  <p className="text-3xl font-bold text-green-900 mt-2">{report.emotionStatistics.interested}%</p>
                </div>
              </div>
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="text-center">
                  <p className="text-sm font-medium text-yellow-600">Bored</p>
                  <p className="text-3xl font-bold text-yellow-900 mt-2">{report.emotionStatistics.bored}%</p>
                </div>
              </div>
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <div className="text-center">
                  <p className="text-sm font-medium text-red-600">Confused</p>
                  <p className="text-3xl font-bold text-red-900 mt-2">{report.emotionStatistics.confused}%</p>
                </div>
              </div>
            </div>
          </div>

          {/* Student Lists */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Present Students */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <CheckCircleIcon className="h-5 w-5 text-green-600 mr-2" />
                Present Students ({presentStudents.length})
              </h3>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 max-h-64 overflow-y-auto">
                <div className="space-y-2">
                  {presentStudents.map((student) => (
                    <div key={student.id} className="flex items-center justify-between bg-white rounded p-2">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{student.name}</p>
                        <p className="text-xs text-gray-600">{student.studentId}</p>
                      </div>
                      <div className="text-xs text-gray-500">
                        {student.gateEntry && (
                          <div className="flex items-center">
                            <ClockIcon className="h-3 w-3 mr-1" />
                            {format(new Date(student.gateEntry), 'HH:mm')}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Absent Students */}
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <XCircleIcon className="h-5 w-5 text-red-600 mr-2" />
                Absent Students ({absentStudents.length})
              </h3>
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 max-h-64 overflow-y-auto">
                <div className="space-y-2">
                  {absentStudents.map((student) => (
                    <div key={student.id} className="flex items-center justify-between bg-white rounded p-2">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{student.name}</p>
                        <p className="text-xs text-gray-600">{student.studentId}</p>
                      </div>
                      <div className="text-xs text-gray-500">
                        {student.type === 'day_scholar' && !student.gateEntry && (
                          <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                            No gate entry
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
          <div className="text-sm text-gray-600">
            Report generated on {format(new Date(), 'MMM dd, yyyy HH:mm')}
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => onExport('pdf')}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors duration-200"
            >
              Export PDF
            </button>
            <button
              onClick={() => onExport('csv')}
              className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors duration-200"
            >
              Export CSV
            </button>
            <button
              onClick={() => onExport('excel')}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors duration-200"
            >
              Export Excel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
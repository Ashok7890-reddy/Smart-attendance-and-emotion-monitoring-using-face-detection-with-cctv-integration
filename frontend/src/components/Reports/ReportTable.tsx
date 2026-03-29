import React from 'react'
import { 
  DocumentArrowDownIcon,
  EyeIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline'
import { AttendanceReport } from '@/types'
import { format } from 'date-fns'

interface ReportTableProps {
  reports: AttendanceReport[]
  isLoading: boolean
  onViewReport: (report: AttendanceReport) => void
  onExportReport: (report: AttendanceReport, format: 'pdf' | 'csv' | 'excel') => void
}

export const ReportTable: React.FC<ReportTableProps> = ({
  reports,
  isLoading,
  onViewReport,
  onExportReport
}) => {
  if (isLoading) {
    return (
      <div className="card">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (reports.length === 0) {
    return (
      <div className="card text-center py-12">
        <ChartBarIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">No Reports Found</h3>
        <p className="text-gray-600">
          No attendance reports found for the selected date range.
        </p>
      </div>
    )
  }

  const getEngagementColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-50'
    if (score >= 60) return 'text-yellow-600 bg-yellow-50'
    return 'text-red-600 bg-red-50'
  }

  const getAttendanceColor = (percentage: number) => {
    if (percentage >= 90) return 'text-green-600 bg-green-50'
    if (percentage >= 75) return 'text-yellow-600 bg-yellow-50'
    return 'text-red-600 bg-red-50'
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          Attendance Reports ({reports.length})
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Session Details
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Attendance
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Engagement
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Duration
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {reports.map((report) => (
              <tr key={report.sessionId} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      Session {report.sessionId.slice(-6)}
                    </div>
                    <div className="text-sm text-gray-500">
                      {format(new Date(report.date), 'MMM dd, yyyy')}
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="text-sm text-gray-900">
                      {report.presentCount}/{report.totalStudents}
                    </div>
                    <span className={`ml-2 inline-flex px-2 py-1 text-xs font-medium rounded-full ${getAttendanceColor(report.attendancePercentage)}`}>
                      {report.attendancePercentage}%
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getEngagementColor(report.engagementScore)}`}>
                    {report.engagementScore}%
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {format(new Date(report.submittedAt), 'HH:mm')}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div className="flex items-center justify-end space-x-2">
                    <button
                      onClick={() => onViewReport(report)}
                      className="text-primary-600 hover:text-primary-900 p-1 rounded"
                      title="View Details"
                    >
                      <EyeIcon className="h-4 w-4" />
                    </button>
                    
                    <div className="relative group">
                      <button className="text-gray-600 hover:text-gray-900 p-1 rounded">
                        <DocumentArrowDownIcon className="h-4 w-4" />
                      </button>
                      
                      {/* Export Dropdown */}
                      <div className="absolute right-0 mt-1 w-32 bg-white rounded-md shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                        <div className="py-1">
                          <button
                            onClick={() => onExportReport(report, 'pdf')}
                            className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          >
                            Export PDF
                          </button>
                          <button
                            onClick={() => onExportReport(report, 'csv')}
                            className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          >
                            Export CSV
                          </button>
                          <button
                            onClick={() => onExportReport(report, 'excel')}
                            className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          >
                            Export Excel
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
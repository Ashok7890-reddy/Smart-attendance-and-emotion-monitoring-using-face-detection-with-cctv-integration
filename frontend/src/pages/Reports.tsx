import React, { useState } from 'react'
import { useReports } from '@/hooks/useReports'
import { DateRangePicker } from '@/components/Reports/DateRangePicker'
import { ReportTable } from '@/components/Reports/ReportTable'
import { ReportDetailModal } from '@/components/Reports/ReportDetailModal'
import { AttendanceReport } from '@/types'

export const Reports: React.FC = () => {
  const {
    reports,
    isLoading,
    startDate,
    endDate,
    setStartDate,
    setEndDate,
    exportReport,
  } = useReports()

  const [selectedReport, setSelectedReport] = useState<AttendanceReport | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleViewReport = (report: AttendanceReport) => {
    setSelectedReport(report)
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedReport(null)
  }

  const handleExportFromTable = async (report: AttendanceReport, format: 'pdf' | 'csv' | 'excel') => {
    try {
      await exportReport(report, format)
    } catch (error) {
      console.error('Export failed:', error)
      // In a real app, show a toast notification
    }
  }

  const handleExportFromModal = async (format: 'pdf' | 'csv' | 'excel') => {
    if (selectedReport) {
      try {
        await exportReport(selectedReport, format)
      } catch (error) {
        console.error('Export failed:', error)
        // In a real app, show a toast notification
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Attendance Reports
            </h2>
            <p className="text-gray-600 mt-1">
              View and export attendance reports with engagement metrics
            </p>
          </div>
          <div className="text-sm text-gray-500">
            {reports.length} report{reports.length !== 1 ? 's' : ''} found
          </div>
        </div>
      </div>

      {/* Date Range Filter */}
      <div className="card">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">
          Filter Reports
        </h3>
        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartDateChange={setStartDate}
          onEndDateChange={setEndDate}
        />
      </div>

      {/* Reports Table */}
      <ReportTable
        reports={reports}
        isLoading={isLoading}
        onViewReport={handleViewReport}
        onExportReport={handleExportFromTable}
      />

      {/* Report Detail Modal */}
      <ReportDetailModal
        report={selectedReport}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onExport={handleExportFromModal}
      />
    </div>
  )
}
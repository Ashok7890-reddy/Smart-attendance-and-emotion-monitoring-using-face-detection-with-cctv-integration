import { useState } from 'react'
import { useQuery } from 'react-query'
import { AttendanceReport } from '@/types'
import { attendanceAPI } from '@/services/api'

export const useReports = () => {
  const [startDate, setStartDate] = useState(() => {
    const date = new Date()
    date.setDate(date.getDate() - 7) // Default to last 7 days
    return date.toISOString().split('T')[0]
  })
  
  const [endDate, setEndDate] = useState(() => {
    return new Date().toISOString().split('T')[0]
  })

  // Query for reports in date range
  const { data: reports = [], isLoading, refetch } = useQuery(
    ['reports', startDate, endDate],
    () => attendanceAPI.getReportsByDateRange(startDate, endDate),
    {
      enabled: !!startDate && !!endDate,
    }
  )

  const exportReport = async (report: AttendanceReport, format: 'pdf' | 'csv' | 'excel') => {
    try {
      // In a real implementation, this would call an API endpoint to generate the export
      console.log(`Exporting report ${report.sessionId} as ${format}`)
      
      // Mock export functionality
      const data = generateExportData(report, format)
      downloadFile(data, `attendance-report-${report.sessionId}.${format}`, format)
      
    } catch (error) {
      console.error('Export failed:', error)
      throw new Error(`Failed to export report as ${format}`)
    }
  }

  const generateExportData = (report: AttendanceReport, format: 'pdf' | 'csv' | 'excel') => {
    if (format === 'csv') {
      // Generate CSV data with engagement metrics
      const headers = [
        'Student ID',
        'Name',
        'Type',
        'Status',
        'Gate Entry',
        'Classroom Entry'
      ]
      
      const rows = report.students.map(student => [
        student.studentId,
        student.name,
        student.type.replace('_', ' '),
        student.isPresent ? 'Present' : 'Absent',
        student.gateEntry ? new Date(student.gateEntry).toLocaleString() : 'N/A',
        student.classroomEntry ? new Date(student.classroomEntry).toLocaleString() : 'N/A'
      ])
      
      // Add summary section
      const summary = [
        [],
        ['SUMMARY'],
        ['Total Students', report.totalStudents.toString()],
        ['Present', report.presentCount.toString()],
        ['Absent', report.absentCount.toString()],
        ['Attendance %', `${report.attendancePercentage}%`],
        [],
        ['ENGAGEMENT METRICS'],
        ['Overall Score', `${report.engagementScore}%`],
        ['Interested', `${report.engagementBreakdown.interested}%`],
        ['Bored', `${report.engagementBreakdown.bored}%`],
        ['Confused', `${report.engagementBreakdown.confused}%`],
        ['Sleepy', `${report.engagementBreakdown.sleepy}%`],
      ]
      
      const csvContent = [headers, ...rows, ...summary]
        .map(row => row.map(field => `"${field}"`).join(','))
        .join('\n')
      
      return csvContent
    }
    
    if (format === 'pdf') {
      // Generate HTML for PDF (can be converted to PDF using browser print)
      const html = `
<!DOCTYPE html>
<html>
<head>
  <title>Attendance Report - ${report.sessionId}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 40px; }
    h1 { color: #333; border-bottom: 2px solid #4F46E5; padding-bottom: 10px; }
    .summary { background: #F3F4F6; padding: 20px; border-radius: 8px; margin: 20px 0; }
    .summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
    .summary-item { text-align: center; }
    .summary-label { font-size: 12px; color: #6B7280; }
    .summary-value { font-size: 24px; font-weight: bold; color: #1F2937; }
    .engagement { margin: 20px 0; }
    .engagement-bar { background: #E5E7EB; height: 30px; border-radius: 4px; margin: 10px 0; position: relative; }
    .engagement-fill { height: 100%; border-radius: 4px; display: flex; align-items: center; padding: 0 10px; color: white; font-weight: bold; }
    .interested { background: #10B981; }
    .bored { background: #F59E0B; }
    .confused { background: #F97316; }
    .sleepy { background: #EF4444; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; }
    th, td { padding: 12px; text-align: left; border-bottom: 1px solid #E5E7EB; }
    th { background: #F9FAFB; font-weight: 600; color: #374151; }
    .present { color: #10B981; font-weight: 600; }
    .absent { color: #EF4444; font-weight: 600; }
    @media print { body { margin: 20px; } }
  </style>
</head>
<body>
  <h1>Attendance Report</h1>
  <p><strong>Session ID:</strong> ${report.sessionId}</p>
  <p><strong>Date:</strong> ${new Date(report.date).toLocaleDateString()}</p>
  
  <div class="summary">
    <h2>Summary</h2>
    <div class="summary-grid">
      <div class="summary-item">
        <div class="summary-label">Total Students</div>
        <div class="summary-value">${report.totalStudents}</div>
      </div>
      <div class="summary-item">
        <div class="summary-label">Present</div>
        <div class="summary-value" style="color: #10B981;">${report.presentCount}</div>
      </div>
      <div class="summary-item">
        <div class="summary-label">Absent</div>
        <div class="summary-value" style="color: #EF4444;">${report.absentCount}</div>
      </div>
    </div>
    <div style="text-align: center; margin-top: 20px;">
      <div class="summary-label">Attendance Rate</div>
      <div class="summary-value" style="font-size: 36px; color: #4F46E5;">${report.attendancePercentage}%</div>
    </div>
  </div>
  
  <div class="engagement">
    <h2>Engagement Metrics</h2>
    <p><strong>Overall Engagement Score:</strong> <span style="font-size: 24px; color: #4F46E5;">${report.engagementScore}%</span></p>
    
    <div class="engagement-bar">
      <div class="engagement-fill interested" style="width: ${report.engagementBreakdown.interested}%">
        😊 Interested ${report.engagementBreakdown.interested}%
      </div>
    </div>
    
    <div class="engagement-bar">
      <div class="engagement-fill bored" style="width: ${report.engagementBreakdown.bored}%">
        😐 Bored ${report.engagementBreakdown.bored}%
      </div>
    </div>
    
    <div class="engagement-bar">
      <div class="engagement-fill confused" style="width: ${report.engagementBreakdown.confused}%">
        😕 Confused ${report.engagementBreakdown.confused}%
      </div>
    </div>
    
    <div class="engagement-bar">
      <div class="engagement-fill sleepy" style="width: ${report.engagementBreakdown.sleepy}%">
        😴 Sleepy ${report.engagementBreakdown.sleepy}%
      </div>
    </div>
  </div>
  
  <h2>Student Details</h2>
  <table>
    <thead>
      <tr>
        <th>Student ID</th>
        <th>Name</th>
        <th>Type</th>
        <th>Status</th>
        <th>Gate Entry</th>
        <th>Classroom Entry</th>
      </tr>
    </thead>
    <tbody>
      ${report.students.map(student => `
        <tr>
          <td>${student.studentId}</td>
          <td>${student.name}</td>
          <td>${student.type.replace('_', ' ')}</td>
          <td class="${student.isPresent ? 'present' : 'absent'}">
            ${student.isPresent ? 'Present' : 'Absent'}
          </td>
          <td>${student.gateEntry ? new Date(student.gateEntry).toLocaleString() : 'N/A'}</td>
          <td>${student.classroomEntry ? new Date(student.classroomEntry).toLocaleString() : 'N/A'}</td>
        </tr>
      `).join('')}
    </tbody>
  </table>
  
  <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #E5E7EB; text-align: center; color: #6B7280; font-size: 12px;">
    Generated on ${new Date().toLocaleString()} | Smart Attendance System
  </div>
</body>
</html>
      `
      return html
    }
    
    // For Excel, return JSON that can be converted
    return JSON.stringify(report, null, 2)
  }

  const downloadFile = (data: string, filename: string, format: string) => {
    if (format === 'pdf') {
      // For PDF, open HTML in new window for printing
      const printWindow = window.open('', '_blank')
      if (printWindow) {
        printWindow.document.write(data)
        printWindow.document.close()
        
        // Auto-print after a short delay
        setTimeout(() => {
          printWindow.print()
        }, 500)
      }
      return
    }
    
    const mimeTypes = {
      csv: 'text/csv',
      excel: 'application/json', // For now, download as JSON
    }
    
    const blob = new Blob([data], { type: mimeTypes[format as keyof typeof mimeTypes] || 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  return {
    reports,
    isLoading,
    startDate,
    endDate,
    setStartDate,
    setEndDate,
    refetch,
    exportReport,
  }
}
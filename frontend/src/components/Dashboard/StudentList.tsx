import React, { useState } from 'react'
import { 
  CheckCircleIcon, 
  XCircleIcon, 
  MagnifyingGlassIcon,
  UserIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { Student } from '@/types'
import { format } from 'date-fns'

interface StudentListProps {
  students: Student[]
  isLoading?: boolean
}

export const StudentList: React.FC<StudentListProps> = ({ students, isLoading }) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [filter, setFilter] = useState<'all' | 'present' | 'absent'>('all')

  const filteredStudents = students.filter(student => {
    const matchesSearch = student.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         student.studentId.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesFilter = filter === 'all' || 
                         (filter === 'present' && student.isPresent) ||
                         (filter === 'absent' && !student.isPresent)
    
    return matchesSearch && matchesFilter
  })

  const presentCount = students.filter(s => s.isPresent).length
  const absentCount = students.filter(s => !s.isPresent).length

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

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-gray-900">
          Student Attendance
        </h3>
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <span className="flex items-center">
            <CheckCircleIcon className="h-4 w-4 text-green-500 mr-1" />
            {presentCount} Present
          </span>
          <span className="flex items-center">
            <XCircleIcon className="h-4 w-4 text-red-500 mr-1" />
            {absentCount} Absent
          </span>
        </div>
      </div>

      {/* Search and Filter */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search students..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="input-field pl-10"
          />
        </div>
        <div className="flex space-x-2">
          {(['all', 'present', 'absent'] as const).map((filterOption) => (
            <button
              key={filterOption}
              onClick={() => setFilter(filterOption)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-200 ${
                filter === filterOption
                  ? 'bg-primary-100 text-primary-700 border border-primary-200'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {filterOption.charAt(0).toUpperCase() + filterOption.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Student List */}
      <div className="space-y-3 max-h-96 overflow-y-auto">
        {filteredStudents.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <UserIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>No students found</p>
          </div>
        ) : (
          filteredStudents.map((student) => (
            <div
              key={student.id}
              className={`flex items-center justify-between p-4 rounded-lg border transition-colors duration-200 ${
                student.isPresent
                  ? 'bg-green-50 border-green-200'
                  : 'bg-red-50 border-red-200'
              }`}
            >
              <div className="flex items-center space-x-4">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  student.isPresent ? 'bg-green-100' : 'bg-red-100'
                }`}>
                  {student.isPresent ? (
                    <CheckCircleIcon className="h-6 w-6 text-green-600" />
                  ) : (
                    <XCircleIcon className="h-6 w-6 text-red-600" />
                  )}
                </div>
                <div>
                  <p className="font-medium text-gray-900">{student.name}</p>
                  <p className="text-sm text-gray-600">ID: {student.studentId}</p>
                  <div className="flex items-center space-x-4 text-xs text-gray-500 mt-1">
                    <span className="capitalize">{student.type.replace('_', ' ')}</span>
                    {student.gateEntry && (
                      <span className="flex items-center">
                        <ClockIcon className="h-3 w-3 mr-1" />
                        Gate: {format(new Date(student.gateEntry), 'HH:mm')}
                      </span>
                    )}
                    {student.classroomEntry && (
                      <span className="flex items-center">
                        <ClockIcon className="h-3 w-3 mr-1" />
                        Class: {format(new Date(student.classroomEntry), 'HH:mm')}
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <div className={`px-3 py-1 rounded-full text-xs font-medium ${
                student.isPresent
                  ? 'bg-green-100 text-green-800'
                  : 'bg-red-100 text-red-800'
              }`}>
                {student.isPresent ? 'Present' : 'Absent'}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
import React from 'react'
import { 
  ExclamationTriangleIcon, 
  XMarkIcon,
  UserIcon 
} from '@heroicons/react/24/outline'
import { Student } from '@/types'

interface MissingStudentAlertProps {
  missingStudents: Student[]
  onDismiss?: () => void
  className?: string
}

export const MissingStudentAlert: React.FC<MissingStudentAlertProps> = ({
  missingStudents,
  onDismiss,
  className = ''
}) => {
  if (missingStudents.length === 0) return null

  return (
    <div className={`card bg-yellow-50 border-yellow-200 ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className="w-8 h-8 bg-yellow-100 rounded-lg flex items-center justify-center flex-shrink-0">
            <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600" />
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-yellow-800 mb-2">
              Missing Students ({missingStudents.length})
            </h4>
            <p className="text-sm text-yellow-700 mb-3">
              The following students are registered but not detected in the classroom:
            </p>
            
            <div className="space-y-2 max-h-32 overflow-y-auto">
              {missingStudents.map((student) => (
                <div
                  key={student.id}
                  className="flex items-center space-x-2 text-sm text-yellow-800 bg-yellow-100 rounded px-3 py-2"
                >
                  <UserIcon className="h-4 w-4 flex-shrink-0" />
                  <span className="font-medium">{student.name}</span>
                  <span className="text-yellow-600">({student.studentId})</span>
                  {student.type === 'day_scholar' && !student.gateEntry && (
                    <span className="text-xs bg-yellow-200 text-yellow-800 px-2 py-1 rounded">
                      No gate entry
                    </span>
                  )}
                </div>
              ))}
            </div>
            
            <div className="mt-3 text-xs text-yellow-700">
              <p>
                • Day scholars require both gate and classroom verification
              </p>
              <p>
                • Hostel students require only classroom verification
              </p>
            </div>
          </div>
        </div>
        
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-yellow-400 hover:text-yellow-600 transition-colors duration-200"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        )}
      </div>
    </div>
  )
}
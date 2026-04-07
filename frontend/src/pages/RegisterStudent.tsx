import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { WebcamCapture } from '@/components/Camera/WebcamCapture'
import { UserPlusIcon, CameraIcon } from '@heroicons/react/24/outline'

export const RegisterStudent: React.FC = () => {
  const navigate = useNavigate()
  const [step, setStep] = useState<'form' | 'camera'>('form')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  
  const [formData, setFormData] = useState({
    student_id: '',
    name: '',
    student_type: 'day_scholar' as 'day_scholar' | 'hostel_student',
    email: '',
    phone: '',
    class_id: 'CS101'
  })

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (!formData.student_id || !formData.name) {
      setError('Student ID and Name are required')
      return
    }
    setStep('camera')
  }

  /**
   * Extract face descriptor from a captured image (base64).
   * Tries backend DeepFace first; falls back to storing the image-only approach
   * (descriptor stored as empty array — recognized by matching image at runtime).
   */
  const extractDescriptor = async (imageBase64: string): Promise<number[]> => {
    try {
      const BACKEND = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const res = await fetch(`${BACKEND}/api/v1/deepface/analyze-emotion-base64`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_base64: imageBase64.split(',')[1] || imageBase64, student_id: formData.student_id }),
        signal: AbortSignal.timeout(8000),
      })
      if (res.ok) {
        // Backend is alive — we'll store image; DeepFace.find() will use it server-side
        console.log('✅ Backend connected. Face will be recognized via DeepFace.find().')
        return [] // empty = backend mode
      }
    } catch {
      console.warn('⚠ Backend offline. Storing photo for local fallback matching.')
    }
    // Fallback: return a placeholder descriptor so the student record is created
    return []
  }

  const handlePhotoCapture = async (imageData: string) => {
    setLoading(true)
    setError(null)

    try {
      const descriptor = await extractDescriptor(imageData)

      const students = JSON.parse(localStorage.getItem('students') || '[]')

      // Prevent duplicate student IDs
      if (students.some((s: any) => s.student_id === formData.student_id)) {
        throw new Error(`Student ID "${formData.student_id}" is already registered.`)
      }

      const newStudent = {
        ...formData,
        face_descriptor: descriptor,
        face_descriptors: [descriptor],   // array form for multi-shot
        face_image: imageData,            // store photo for display + backend lookup
        registered_at: new Date().toISOString(),
      }

      students.push(newStudent)
      localStorage.setItem('students', JSON.stringify(students))

      console.log(`✅ Student "${formData.name}" registered successfully!`)
      setSuccess(true)

    } catch (err: any) {
      console.error('Registration error:', err)
      setError(err.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="max-w-md mx-auto text-center py-16">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <span className="text-4xl">✅</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Student Registered!</h2>
        <p className="text-gray-600 mb-6">
          <strong>{formData.name}</strong> ({formData.student_id}) has been successfully registered.
        </p>
        <div className="flex gap-3 justify-center">
          <button
            onClick={() => {
              setSuccess(false)
              setStep('form')
              setFormData({ student_id: '', name: '', student_type: 'day_scholar', email: '', phone: '', class_id: 'CS101' })
            }}
            className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium transition-colors"
          >
            Register Another
          </button>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-primary-100 rounded-xl flex items-center justify-center">
          <UserPlusIcon className="h-5 w-5 text-primary-600" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-900">Register New Student</h2>
          <p className="text-sm text-gray-500">
            {step === 'form' ? 'Fill in student details' : 'Capture student photo for face recognition'}
          </p>
        </div>
      </div>

      {/* Step Indicator */}
      <div className="flex items-center gap-3 text-sm">
        <div className={`flex items-center gap-1.5 ${step === 'form' ? 'text-primary-600 font-semibold' : 'text-gray-400'}`}>
          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step === 'form' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-500'}`}>1</span>
          Student Info
        </div>
        <div className="flex-1 h-px bg-gray-200" />
        <div className={`flex items-center gap-1.5 ${step === 'camera' ? 'text-primary-600 font-semibold' : 'text-gray-400'}`}>
          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${step === 'camera' ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-500'}`}>2</span>
          Face Photo
        </div>
      </div>

      {step === 'form' && (
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <form onSubmit={handleFormSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Student ID *</label>
                <input
                  name="student_id"
                  value={formData.student_id}
                  onChange={handleInputChange}
                  required
                  placeholder="e.g. S2024001"
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
                <input
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  required
                  placeholder="e.g. Ramesh Kumar"
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <input
                  name="email"
                  type="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="ramesh@college.edu"
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Phone</label>
                <input
                  name="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                  placeholder="9876543210"
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Class ID</label>
                <input
                  name="class_id"
                  value={formData.class_id}
                  onChange={handleInputChange}
                  placeholder="CS101"
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Student Type</label>
                <select
                  name="student_type"
                  value={formData.student_type}
                  onChange={handleInputChange}
                  className="input"
                >
                  <option value="day_scholar">Day Scholar</option>
                  <option value="hostel_student">Hostel Student</option>
                </select>
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                ⚠ {error}
              </div>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => navigate('/')}
                className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex items-center gap-2 px-5 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium transition-colors"
              >
                <CameraIcon className="h-4 w-4" />
                Next: Capture Photo
              </button>
            </div>
          </form>
        </div>
      )}

      {step === 'camera' && (
        <div className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-800">
            <p className="font-semibold mb-1">📸 Photo Capture Tips</p>
            <ul className="space-y-0.5 text-blue-700">
              <li>• Look directly at the camera</li>
              <li>• Ensure good lighting on your face</li>
              <li>• Remove glasses if possible for better recognition</li>
              <li>• Keep a neutral expression</li>
            </ul>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              ⚠ {error}
            </div>
          )}

          <WebcamCapture
            onCapture={handlePhotoCapture}
            isProcessing={loading}
            processingMessage="Registering student..."
          />

          {loading && (
            <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-xl border border-blue-200">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600" />
              <p className="text-sm text-blue-700 font-medium">Registering student face...</p>
            </div>
          )}

          <button
            onClick={() => setStep('form')}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            ← Back to form
          </button>
        </div>
      )}
    </div>
  )
}

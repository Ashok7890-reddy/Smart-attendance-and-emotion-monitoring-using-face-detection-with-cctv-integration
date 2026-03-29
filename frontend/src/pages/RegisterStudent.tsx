import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { WebcamCapture } from '@/components/Camera/WebcamCapture'
import { UserPlusIcon, CameraIcon } from '@heroicons/react/24/outline'
import { enhancedFaceService } from '@/services/enhancedFaceService'

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
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
  }

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    
    // Validate form
    if (!formData.student_id || !formData.name) {
      setError('Student ID and Name are required')
      return
    }
    
    // Move to camera step
    setStep('camera')
  }

  const handlePhotoCapture = async (imageData: string) => {
    setLoading(true)
    setError(null)

    try {
      console.log('🔍 Detecting face with REAL ML...')
      
      // Create optimized image element from base64
      const img = await enhancedFaceService.createImageElement(imageData)

      // Detect face and extract descriptor (embedding) using enhanced service
      const detection = await enhancedFaceService.detectFace(img)
      
      if (!detection) {
        throw new Error('No face detected. Please ensure your face is clearly visible and try again.')
      }

      console.log('✅ Face detected! Confidence:', detection.detection.score.toFixed(3))
      console.log('🎯 Model used:', detection.modelUsed)
      console.log('📊 Embedding dimensions:', detection.descriptor.length + 'D (' + detection.embeddingDimension + 'D)')
      console.log('⚡ Processing time:', detection.processingTime?.toFixed(1) + 'ms')
      
      // Check face quality
      const faceScore = detection.detection.score
      if (faceScore < 0.8) {
        console.warn('⚠️ Low face detection confidence. Try better lighting or angle.')
      }
      
      // Check face size
      const faceBox = detection.detection.box
      const faceArea = faceBox.width * faceBox.height
      console.log('Face area:', Math.round(faceArea), 'pixels')
      
      if (faceArea < 10000) {
        console.warn('⚠️ Face is small. Move closer to camera for better recognition.')
      }
      
      // Enhanced descriptor quality assessment
      const qualityAssessment = enhancedFaceService.assessImageQuality(img)
      console.log('Image quality assessment:', qualityAssessment.quality, '(score:', qualityAssessment.score + ')')
      
      if (qualityAssessment.recommendations.length > 0) {
        console.warn('⚠️ Image quality recommendations:')
        qualityAssessment.recommendations.forEach(rec => console.warn('  •', rec))
      }
      
      // Check descriptor quality based on model type
      const descriptorSum = detection.descriptor.reduce((sum: number, val: number) => sum + Math.abs(val), 0)
      console.log('Descriptor quality score:', descriptorSum.toFixed(3))
      
      const isONNX = detection.modelUsed?.includes('ONNX')
      const minQualityThreshold = isONNX ? 0.8 : 5.0 // Different thresholds for different models
      const minNonZeroCount = isONNX ? 400 : 100 // ONNX has 512D vs 128D
      
      if (descriptorSum < minQualityThreshold) {
        console.warn('⚠️ Low quality face descriptor. Try better lighting or retake photo.')
      }
      
      // Validate descriptor has meaningful values
      const nonZeroCount = detection.descriptor.filter((val: number) => Math.abs(val) > 0.001).length
      const totalDimensions = detection.descriptor.length
      console.log('Non-zero descriptor values:', nonZeroCount, '/', totalDimensions)
      
      if (nonZeroCount < minNonZeroCount) {
        throw new Error('Poor quality face capture. Please ensure good lighting and try again.')
      }

      // Store student with enhanced face descriptor
      const students = JSON.parse(localStorage.getItem('students') || '[]')
      const newStudent = {
        ...formData,
        face_descriptor: Array.from(detection.descriptor), // High-quality embedding (128D or 512D)
        face_image: imageData, // Optional: store image for display
        registered_at: new Date().toISOString(),
        model_used: detection.modelUsed, // Track which model was used for registration
        embedding_dimension: detection.embeddingDimension, // Track embedding dimension
        registration_quality: qualityAssessment.quality, // Store quality assessment
        processing_time: detection.processingTime // Store processing performance
      }
      
      students.push(newStudent)
      localStorage.setItem('students', JSON.stringify(students))
      
      console.log('✅ Student registered with enhanced face recognition!')
      console.log('📊 Registration details:')
      console.log('  • Model:', detection.modelUsed)
      console.log('  • Embedding:', detection.embeddingDimension + 'D')
      console.log('  • Quality:', qualityAssessment.quality)
      console.log('  • Processing time:', detection.processingTime?.toFixed(1) + 'ms')
      console.log('Total students:', students.length)
      
      setSuccess(true)
      
      setTimeout(() => navigate('/'), 2000)
    } catch (err: any) {
      console.error('Registration error:', err)
      setError(err.message || 'Failed to register student')
      setStep('form')
    } finally {
      setLoading(false)
    }
  }

  const handleCameraCancel = () => {
    setStep('form')
  }

  if (success) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Registration Successful!</h2>
          <p className="text-gray-600">Student has been registered successfully.</p>
          <p className="text-sm text-gray-500 mt-4">Redirecting to dashboard...</p>
        </div>
      </div>
    )
  }

  if (step === 'camera') {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="mb-6">
            <button
              onClick={() => navigate('/')}
              className="text-primary-600 hover:text-primary-700 font-medium"
            >
              ← Back to Dashboard
            </button>
          </div>
          
          <WebcamCapture
            title={`Register Face for ${formData.name}`}
            subtitle="Position your face in the oval guide and capture a clear photo"
            onCapture={handlePhotoCapture}
            onCancel={handleCameraCancel}
          />

          {loading && (
            <div className="mt-4 text-center">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
              <p className="mt-2 text-gray-600">Registering student...</p>
            </div>
          )}

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-2xl mx-auto">
        <div className="mb-6">
          <button
            onClick={() => navigate('/')}
            className="text-primary-600 hover:text-primary-700 font-medium"
          >
            ← Back to Dashboard
          </button>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="flex items-center mb-6">
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center mr-4">
              <UserPlusIcon className="h-6 w-6 text-primary-600" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Register New Student</h1>
              <p className="text-sm text-gray-600">Fill in student details and capture photo</p>
            </div>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          <form onSubmit={handleFormSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label htmlFor="student_id" className="block text-sm font-medium text-gray-700 mb-2">
                  Student ID *
                </label>
                <input
                  type="text"
                  id="student_id"
                  name="student_id"
                  value={formData.student_id}
                  onChange={handleInputChange}
                  placeholder="99220041951"
                  className="input-field w-full"
                  required
                />
              </div>

              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
                  Full Name *
                </label>
                <input
                  type="text"
                  id="name"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="Student Name"
                  className="input-field w-full"
                  required
                />
              </div>

              <div>
                <label htmlFor="student_type" className="block text-sm font-medium text-gray-700 mb-2">
                  Student Type *
                </label>
                <select
                  id="student_type"
                  name="student_type"
                  value={formData.student_type}
                  onChange={handleInputChange}
                  className="input-field w-full"
                  required
                >
                  <option value="day_scholar">Day Scholar</option>
                  <option value="hostel_student">Hostel Student</option>
                </select>
              </div>

              <div>
                <label htmlFor="class_id" className="block text-sm font-medium text-gray-700 mb-2">
                  Class ID *
                </label>
                <input
                  type="text"
                  id="class_id"
                  name="class_id"
                  value={formData.class_id}
                  onChange={handleInputChange}
                  placeholder="CS101"
                  className="input-field w-full"
                  required
                />
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  placeholder="student@example.com"
                  className="input-field w-full"
                />
              </div>

              <div>
                <label htmlFor="phone" className="block text-sm font-medium text-gray-700 mb-2">
                  Phone
                </label>
                <input
                  type="tel"
                  id="phone"
                  name="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                  placeholder="+91-9876543210"
                  className="input-field w-full"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-4 pt-6 border-t">
              <button
                type="button"
                onClick={() => navigate('/')}
                className="px-6 py-3 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex items-center px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
              >
                <CameraIcon className="h-5 w-5 mr-2" />
                Next: Capture Photo
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

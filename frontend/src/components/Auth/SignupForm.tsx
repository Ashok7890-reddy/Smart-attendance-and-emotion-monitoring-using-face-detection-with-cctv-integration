import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { EyeIcon, EyeSlashIcon, UserIcon, EnvelopeIcon, LockClosedIcon } from '@heroicons/react/24/outline'
import { useAuthStore } from '@/store/authStore'

interface SignupFormData {
  fullName: string
  email: string
  password: string
  confirmPassword: string
}

interface SignupFormProps {
  onSwitchToLogin: () => void
}

export const SignupForm: React.FC<SignupFormProps> = ({ onSwitchToLogin }) => {
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  
  const { signup } = useAuthStore()
  
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<SignupFormData>()

  const password = watch('password')

  // Helper function to get username from email
  const getUsernameFromEmail = (email: string): string => {
    return email.split('@')[0]
  }

  const onSubmit = async (data: SignupFormData) => {
    setIsLoading(true)
    setError('')
    setSuccess('')
    
    try {
      await signup(data.email, data.password, data.fullName)
      setSuccess('Account created successfully! You are now logged in.')
    } catch (err: any) {
      setError(err.message || 'Failed to create account')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-300 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}
      
      {success && (
        <div className="bg-green-500/10 border border-green-500/20 text-green-300 px-4 py-3 rounded-lg text-sm">
          {success}
        </div>
      )}
      
      <div className="space-y-4">
        {/* Full Name Input */}
        <div className="relative">
          <input
            {...register('fullName', {
              required: 'Full name is required',
              minLength: {
                value: 2,
                message: 'Name must be at least 2 characters',
              },
            })}
            type="text"
            className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30 focus:border-cyan-400/30 backdrop-blur-md transition-all duration-300 text-center"
            placeholder="Full Name"
          />
          {errors.fullName && (
            <p className="mt-1 text-sm text-red-300">{errors.fullName.message}</p>
          )}
        </div>

        {/* Email Input */}
        <div className="relative">
          <input
            {...register('email', {
              required: 'Email is required',
              pattern: {
                value: /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$/i,
                message: 'Invalid email address',
              },
            })}
            type="email"
            className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30 focus:border-cyan-400/30 backdrop-blur-md transition-all duration-300 text-center"
            placeholder="Email Address"
          />
          {errors.email && (
            <p className="mt-1 text-sm text-red-300">{errors.email.message}</p>
          )}
          
          {/* Show username preview */}
          {watch('email') && !errors.email && (
            <p className="mt-1 text-sm text-cyan-300 text-center">
              Username: <strong>@{getUsernameFromEmail(watch('email'))}</strong>
            </p>
          )}
        </div>

        {/* Password Input */}
        <div className="relative">
          <input
            {...register('password', {
              required: 'Password is required',
              minLength: {
                value: 6,
                message: 'Password must be at least 6 characters',
              },
            })}
            type={showPassword ? 'text' : 'password'}
            className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30 focus:border-cyan-400/30 backdrop-blur-md transition-all duration-300 text-center"
            placeholder="Password"
          />
          <button
            type="button"
            className="absolute right-4 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white/60 transition-colors"
            onClick={() => setShowPassword(!showPassword)}
          >
            {showPassword ? (
              <EyeSlashIcon className="h-4 w-4" />
            ) : (
              <EyeIcon className="h-4 w-4" />
            )}
          </button>
          {errors.password && (
            <p className="mt-1 text-sm text-red-300">{errors.password.message}</p>
          )}
        </div>

        {/* Confirm Password Input */}
        <div className="relative">
          <input
            {...register('confirmPassword', {
              required: 'Please confirm your password',
              validate: (value) =>
                value === password || 'Passwords do not match',
            })}
            type={showConfirmPassword ? 'text' : 'password'}
            className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30 focus:border-cyan-400/30 backdrop-blur-md transition-all duration-300 text-center"
            placeholder="Confirm Password"
          />
          <button
            type="button"
            className="absolute right-4 top-1/2 transform -translate-y-1/2 text-white/40 hover:text-white/60 transition-colors"
            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
          >
            {showConfirmPassword ? (
              <EyeSlashIcon className="h-4 w-4" />
            ) : (
              <EyeIcon className="h-4 w-4" />
            )}
          </button>
          {errors.confirmPassword && (
            <p className="mt-1 text-sm text-red-300">{errors.confirmPassword.message}</p>
          )}
        </div>
      </div>

      {/* Signup Button */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-4 px-4 bg-white/10 hover:bg-white/15 border border-white/20 hover:border-white/30 text-white font-medium rounded-xl transition-all duration-300 backdrop-blur-md focus:outline-none focus:ring-1 focus:ring-cyan-400/30 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
            Creating Account...
          </div>
        ) : (
          'Sign Up'
        )}
      </button>

      {/* Switch to Login */}
      <div className="text-center">
        <button
          type="button"
          onClick={onSwitchToLogin}
          className="text-white/80 hover:text-white text-sm transition-colors"
        >
          Already have an account?{' '}
          <span className="text-cyan-400 hover:text-cyan-300 font-medium">Sign in</span>
        </button>
      </div>
    </form>
  )
}
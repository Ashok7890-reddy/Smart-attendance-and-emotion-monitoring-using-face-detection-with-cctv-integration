import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { EyeIcon, EyeSlashIcon, UserIcon, LockClosedIcon } from '@heroicons/react/24/outline'
import { useAuthStore } from '@/store/authStore'

interface LoginFormData {
  email: string
  password: string
}

interface LoginFormProps {
  onSwitchToSignup: () => void
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSwitchToSignup }) => {
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  
  const { login } = useAuthStore()
  
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>()

  const onSubmit = async (data: LoginFormData) => {
    setIsLoading(true)
    setError('')
    
    try {
      await login(data.email, data.password)
    } catch (err: any) {
      setError(err.message || 'Invalid email or password')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <form className="space-y-6" onSubmit={handleSubmit(onSubmit)}>
      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-300 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}
      
      <div className="space-y-4">
        {/* Username/Email Input - Matching the image style */}
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
            autoComplete="email"
            className="w-full px-4 py-4 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/50 focus:outline-none focus:ring-1 focus:ring-cyan-400/30 focus:border-cyan-400/30 backdrop-blur-md transition-all duration-300 text-center"
            placeholder="Email Address"
          />
          {errors.email && (
            <p className="mt-1 text-sm text-red-300">{errors.email.message}</p>
          )}
        </div>

        {/* Password Input - Matching the image style */}
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
            autoComplete="current-password"
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
      </div>

      {/* Login Button - Matching the image style */}
      <button
        type="submit"
        disabled={isLoading}
        className="w-full py-4 px-4 bg-white/10 hover:bg-white/15 border border-white/20 hover:border-white/30 text-white font-medium rounded-xl transition-all duration-300 backdrop-blur-md focus:outline-none focus:ring-1 focus:ring-cyan-400/30 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? (
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
            Signing in...
          </div>
        ) : (
          'Log In'
        )}
      </button>

      {/* Switch to Signup */}
      <div className="text-center">
        <button
          type="button"
          onClick={onSwitchToSignup}
          className="text-white/80 hover:text-white text-sm transition-colors"
        >
          Don't have an account?{' '}
          <span className="text-cyan-400 hover:text-cyan-300 font-medium">Sign up</span>
        </button>
      </div>
    </form>
  )
}
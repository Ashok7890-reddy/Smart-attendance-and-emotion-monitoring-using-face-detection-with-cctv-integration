import React, { useState } from 'react'
import { LoginForm } from './LoginForm'
import { SignupForm } from './SignupForm'

export const AuthPage: React.FC = () => {
  const [isLogin, setIsLogin] = useState(true)

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Background - Modern office/tech environment with blur */}
      <div 
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{
          backgroundImage: `linear-gradient(135deg, rgba(30, 58, 138, 0.3) 0%, rgba(67, 56, 202, 0.3) 50%, rgba(59, 130, 246, 0.3) 100%), 
                           linear-gradient(rgba(15, 23, 42, 0.7), rgba(30, 41, 59, 0.8)),
                           url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080"><rect fill="%23334155" width="1920" height="1080"/><g fill="%23475569" opacity="0.4"><rect x="200" y="150" width="300" height="200" rx="10"/><rect x="600" y="300" width="250" height="150" rx="8"/><rect x="1000" y="200" width="400" height="250" rx="12"/><rect x="1500" y="400" width="200" height="300" rx="6"/><circle cx="300" cy="600" r="80"/><circle cx="800" cy="700" r="60"/><circle cx="1200" cy="800" r="100"/></g></svg>')`
        }}
      />

      {/* Animated network connections */}
      <div className="absolute inset-0">
        <svg className="w-full h-full opacity-20" viewBox="0 0 1920 1080">
          <defs>
            <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.6"/>
              <stop offset="50%" stopColor="#8b5cf6" stopOpacity="0.4"/>
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.6"/>
            </linearGradient>
          </defs>
          
          {/* Network lines */}
          <line x1="200" y1="200" x2="800" y2="400" stroke="url(#lineGradient)" strokeWidth="1"/>
          <line x1="800" y1="400" x2="1200" y2="300" stroke="url(#lineGradient)" strokeWidth="1"/>
          <line x1="1200" y1="300" x2="1500" y2="600" stroke="url(#lineGradient)" strokeWidth="1"/>
          <line x1="400" y1="700" x2="1000" y2="500" stroke="url(#lineGradient)" strokeWidth="1"/>
          
          {/* Network nodes */}
          <circle cx="200" cy="200" r="4" fill="#06b6d4" opacity="0.8">
            <animate attributeName="opacity" values="0.4;1;0.4" dur="2s" repeatCount="indefinite"/>
          </circle>
          <circle cx="800" cy="400" r="4" fill="#8b5cf6" opacity="0.8">
            <animate attributeName="opacity" values="0.4;1;0.4" dur="2.5s" repeatCount="indefinite"/>
          </circle>
          <circle cx="1200" cy="300" r="4" fill="#3b82f6" opacity="0.8">
            <animate attributeName="opacity" values="0.4;1;0.4" dur="3s" repeatCount="indefinite"/>
          </circle>
          <circle cx="1500" cy="600" r="4" fill="#06b6d4" opacity="0.8">
            <animate attributeName="opacity" values="0.4;1;0.4" dur="2.2s" repeatCount="indefinite"/>
          </circle>
        </svg>
      </div>

      {/* Floating particles */}
      <div className="absolute inset-0">
        {[...Array(15)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-cyan-400 rounded-full opacity-60"
            style={{
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              animation: `float 6s ease-in-out infinite ${Math.random() * 3}s`,
              animationDirection: Math.random() > 0.5 ? 'normal' : 'reverse'
            }}
          />
        ))}
      </div>

      {/* Main content */}
      <div className="relative z-10 min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-md w-full">
          {/* Geometric Face Icon - Exactly matching the image design */}
          <div className="text-center mb-8">
            <div className="relative mx-auto w-48 h-48 mb-6">
              {/* Main wireframe face - More detailed to match the image */}
              <svg 
                className="w-full h-full" 
                viewBox="0 0 240 240" 
                fill="none" 
                xmlns="http://www.w3.org/2000/svg"
              >
                <defs>
                  <linearGradient id="faceGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#00d4ff" stopOpacity="0.9"/>
                    <stop offset="30%" stopColor="#06b6d4" stopOpacity="0.8"/>
                    <stop offset="70%" stopColor="#8b5cf6" stopOpacity="0.7"/>
                    <stop offset="100%" stopColor="#d946ef" stopOpacity="0.9"/>
                  </linearGradient>
                  <filter id="glow">
                    <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                    <feMerge> 
                      <feMergeNode in="coloredBlur"/>
                      <feMergeNode in="SourceGraphic"/>
                    </feMerge>
                  </filter>
                </defs>
                
                {/* Face outline - triangular mesh pattern */}
                {/* Top of head */}
                <path d="M120 20 L90 50 L120 60 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.8" filter="url(#glow)"/>
                <path d="M120 20 L150 50 L120 60 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.8" filter="url(#glow)"/>
                
                {/* Forehead area */}
                <path d="M90 50 L70 80 L90 90 L120 60 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.7"/>
                <path d="M150 50 L170 80 L150 90 L120 60 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.7"/>
                <path d="M90 90 L120 60 L150 90 L120 100 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.8"/>
                
                {/* Eye regions */}
                <path d="M70 80 L50 110 L80 120 L90 90 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.9"/>
                <path d="M170 80 L190 110 L160 120 L150 90 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.9"/>
                
                {/* Central face area */}
                <path d="M90 90 L80 120 L120 130 L120 100 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.8"/>
                <path d="M150 90 L160 120 L120 130 L120 100 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.8"/>
                
                {/* Nose area */}
                <path d="M120 100 L110 130 L120 150 L130 130 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.9"/>
                
                {/* Mouth and lower face */}
                <path d="M80 120 L60 150 L90 170 L110 130 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.7"/>
                <path d="M160 120 L180 150 L150 170 L130 130 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.7"/>
                <path d="M110 130 L90 170 L120 180 L120 150 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.8"/>
                <path d="M130 130 L150 170 L120 180 L120 150 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.8"/>
                
                {/* Chin area */}
                <path d="M90 170 L70 200 L120 210 L120 180 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.6"/>
                <path d="M150 170 L170 200 L120 210 L120 180 Z" stroke="url(#faceGradient)" strokeWidth="1.2" fill="none" opacity="0.6"/>
                
                {/* Connection lines for network effect */}
                <line x1="120" y1="20" x2="120" y2="60" stroke="url(#faceGradient)" strokeWidth="0.8" opacity="0.6"/>
                <line x1="90" y1="50" x2="150" y2="50" stroke="url(#faceGradient)" strokeWidth="0.8" opacity="0.5"/>
                <line x1="70" y1="80" x2="170" y2="80" stroke="url(#faceGradient)" strokeWidth="0.8" opacity="0.5"/>
                <line x1="80" y1="120" x2="160" y2="120" stroke="url(#faceGradient)" strokeWidth="0.8" opacity="0.5"/>
                <line x1="120" y1="100" x2="120" y2="150" stroke="url(#faceGradient)" strokeWidth="0.8" opacity="0.6"/>
                <line x1="90" y1="170" x2="150" y2="170" stroke="url(#faceGradient)" strokeWidth="0.8" opacity="0.5"/>
              </svg>
              
              {/* Floating connection points - more like the image */}
              {[...Array(16)].map((_, i) => (
                <div
                  key={i}
                  className="absolute w-1 h-1 bg-cyan-300 rounded-full opacity-70"
                  style={{
                    left: `${50 + 40 * Math.cos((i * Math.PI * 2) / 16)}%`,
                    top: `${50 + 40 * Math.sin((i * Math.PI * 2) / 16)}%`,
                    animation: `pulse 4s infinite ${i * 0.2}s`,
                    boxShadow: '0 0 4px #00d4ff'
                  }}
                />
              ))}
              
              {/* Additional network nodes */}
              {[...Array(8)].map((_, i) => (
                <div
                  key={`inner-${i}`}
                  className="absolute w-0.5 h-0.5 bg-purple-300 rounded-full opacity-60"
                  style={{
                    left: `${50 + 25 * Math.cos((i * Math.PI * 2) / 8)}%`,
                    top: `${50 + 25 * Math.sin((i * Math.PI * 2) / 8)}%`,
                    animation: `pulse 3s infinite ${i * 0.3}s`,
                    boxShadow: '0 0 2px #d946ef'
                  }}
                />
              ))}
            </div>

            {/* Title - Exactly matching the image */}
            <h1 className="text-2xl font-bold text-white mb-2 tracking-[0.2em] uppercase font-light">
              SMART FACIAL SYSTEM ATTENDANCE
            </h1>
          </div>

          {/* Glass morphism form container - Matching the image style */}
          <div className="backdrop-blur-lg bg-white/5 rounded-2xl border border-white/10 shadow-2xl p-8">
            {/* Form */}
            {isLogin ? (
              <LoginForm onSwitchToSignup={() => setIsLogin(false)} />
            ) : (
              <SignupForm onSwitchToLogin={() => setIsLogin(true)} />
            )}
          </div>

          {/* Footer */}
          <div className="mt-6 text-center">
            <p className="text-sm text-white/80">
              Smart Attendance System v2.0
            </p>
            <p className="text-xs text-white/60 mt-1">
              Secure faculty authentication system
            </p>
          </div>
        </div>
      </div>

      {/* CSS for animations */}
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes float {
          0%, 100% { transform: translateY(0px) translateX(0px); }
          25% { transform: translateY(-10px) translateX(5px); }
          50% { transform: translateY(-5px) translateX(-5px); }
          75% { transform: translateY(-15px) translateX(3px); }
        }
      ` }} />
    </div>
  )
}